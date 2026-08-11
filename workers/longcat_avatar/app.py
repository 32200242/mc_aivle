from __future__ import annotations

import base64
import binascii
import json
import math
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


MODEL_ID = "meituan-longcat/LongCat-Video-Avatar-1.5"
ROOT = Path(os.getenv("LONGCAT_WORKER_ROOT", "/content/longcat_avatar_worker"))
REPO = Path(os.getenv("LONGCAT_REPO", "/content/longcat_avatar15/repo"))
PYTHON = Path(os.getenv("LONGCAT_PYTHON", "/content/longcat_avatar15/.venv/bin/python"))
CHECKPOINT = Path(
    os.getenv(
        "LONGCAT_CHECKPOINT",
        "/content/longcat_avatar15/weights/LongCat-Video-Avatar-1.5",
    )
)
LOWMEM_SCRIPT = Path(
    os.getenv(
        "LONGCAT_LOWMEM_SCRIPT",
        str(REPO / "run_demo_avatar_single_lowmem.py"),
    )
)
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_BIN", "ffprobe")
RESOLUTION = os.getenv("LONGCAT_RESOLUTION", "480p")
API_KEY = os.getenv("LONGCAT_WORKER_API_KEY", "")
SEED = int(os.getenv("LONGCAT_SEED", "29411"))
MAX_INPUT_MB = int(os.getenv("LONGCAT_MAX_INPUT_MB", "25"))

MEDIA_DIR = ROOT / "media"
JOB_DIR = ROOT / "jobs"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
JOB_DIR.mkdir(parents=True, exist_ok=True)

# Low-memory inference is deliberately serialized. The web application remains
# responsive because this process is deployed separately from LLM/TTS/STT.
GPU_LOCK = threading.Lock()

app = FastAPI(title="LongCat Avatar 1.5 GPU Worker", version="0.1.0")


class AvatarRenderRequest(BaseModel):
    turn_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=4000)
    emotion: str = "neutral"
    persona_id: str = "lee-jieun"
    source_image_base64: str = Field(min_length=100)
    source_image_mime_type: str = "image/png"
    audio_url: str = Field(min_length=10)
    cache_key: str | None = None


def _authorize(authorization: str | None) -> None:
    if not API_KEY:
        return
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid worker API key")


def _safe_name(value: str | None, fallback: str = "turn") -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]", "", value or "")[:120]
    return normalized or fallback


def _decode_image(value: str) -> bytes:
    encoded = value.split(",", 1)[1] if value.startswith("data:") else value
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="Invalid source image") from exc
    if not raw or len(raw) > MAX_INPUT_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Source image is empty or too large")
    return raw


def _read_audio(value: str) -> bytes:
    if value.startswith("data:"):
        try:
            return base64.b64decode(value.split(",", 1)[1], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise HTTPException(status_code=422, detail="Invalid audio data URL") from exc
    request = urllib.request.Request(
        value,
        headers={"Accept": "audio/*", "ngrok-skip-browser-warning": "1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read(MAX_INPUT_MB * 1024 * 1024 + 1)
    if not raw or len(raw) > MAX_INPUT_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio is empty or too large")
    return raw


def _duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _num_segments(duration: float) -> int:
    first_segment_seconds = 93 / 25
    following_segment_seconds = (93 - 13) / 25
    return max(
        1,
        1 + math.ceil(max(0.0, duration - first_segment_seconds) / following_segment_seconds),
    )


def _prompt(emotion: str) -> str:
    emotional_detail = {
        "hurt": (
            "She feels quietly hurt and disappointed, never angry. Hurt is shown by a "
            "softened gaze, slight inner-eyebrow lift and subtle lip tension. Her eyebrows "
            "never pull downward or strongly together; the glabella remains smooth."
        ),
        "sad": "She looks gently sad and reflective without crying, grimacing or melodrama.",
        "anxious": "She looks mildly cautious, with calm breathing and no panic performance.",
        "angry": "She is frustrated but socially restrained, never aggressive or threatening.",
        "withdrawn": "She is reserved and quiet, with subdued eye contact and no dramatic motion.",
        "neutral": "She remains calm, attentive and emotionally neutral.",
    }.get(emotion, "She remains calm and emotionally restrained.")
    return " ".join(
        [
            "Locked-off medium close-up in a quiet family counseling room.",
            "A Korean adult client speaks softly to the counselor.",
            emotional_detail,
            "Accurate lip shapes, natural jaw and chin motion, and minimal lower-cheek support.",
            "Two or three slow irregular blinks, tiny eye refocusing and quiet breathing.",
            "The head is almost still and the crown, hairline, ears, neck and shoulders remain coherent.",
            "The expression stays close to the source portrait and never accumulates across the shot.",
            "No exaggerated acting, repeated motion, camera movement, face warping or identity drift.",
        ]
    )


def _assert_runtime_ready() -> None:
    missing = [path for path in (REPO, PYTHON, CHECKPOINT, LOWMEM_SCRIPT) if not path.exists()]
    if missing:
        raise HTTPException(
            status_code=503,
            detail="LongCat worker is not provisioned: " + ", ".join(map(str, missing)),
        )
    script = LOWMEM_SCRIPT.read_text(encoding="utf-8")
    patched = script.replace(
        "generator.manual_seed(42 + global_rank)",
        "generator.manual_seed(int(os.environ.get('LONGCAT_SEED', '42')) + global_rank)",
    ).replace("offload_kv_cache=False", "offload_kv_cache=True")
    if patched != script:
        LOWMEM_SCRIPT.write_text(patched, encoding="utf-8")


@app.get("/v1/avatar/status")
def status(authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    missing = [str(path) for path in (REPO, PYTHON, CHECKPOINT, LOWMEM_SCRIPT) if not path.exists()]
    gpu = None
    try:
        gpu = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            text=True,
            timeout=5,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "status": "ok" if not missing and gpu else "not_ready",
        "provider": "longcat_avatar_15_lowmem",
        "model": MODEL_ID,
        "resolution": RESOLUTION,
        "gpu": gpu,
        "missing": missing,
        "concurrency": 1,
    }


@app.post("/v1/avatar/render")
def render(
    payload: AvatarRenderRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _authorize(authorization)
    _assert_runtime_ready()
    safe_id = _safe_name(payload.cache_key or payload.turn_id)
    final_path = MEDIA_DIR / f"{safe_id}.mp4"
    if final_path.exists() and final_path.stat().st_size > 100_000:
        return {
            "provider": "longcat_avatar_15_lowmem",
            "model": MODEL_ID,
            "video_url": f"/v1/avatar/media/{final_path.name}",
            "cached": True,
            "render_ms": 0,
        }

    started = time.perf_counter()
    work = JOB_DIR / f"{safe_id}-{int(started * 1000)}"
    work.mkdir(parents=True, exist_ok=False)
    source_image = work / "source.png"
    source_audio = work / "speech_input"
    normalized_audio = work / "speech.wav"
    source_image.write_bytes(_decode_image(payload.source_image_base64))
    source_audio.write_bytes(_read_audio(payload.audio_url))

    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-v",
            "warning",
            "-i",
            str(source_audio),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(normalized_audio),
        ],
        check=True,
    )
    duration = _duration_seconds(normalized_audio)
    segments = _num_segments(duration)
    job_json = work / "job.json"
    job_json.write_text(
        json.dumps(
            {
                "prompt": _prompt(payload.emotion),
                "cond_image": str(source_image),
                "cond_audio": {"person1": str(normalized_audio)},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    generated_dir = work / "generated"
    generated_dir.mkdir()
    command = [
        str(PYTHON),
        "-m",
        "torch.distributed.run",
        "--nproc_per_node=1",
        str(LOWMEM_SCRIPT),
        "--checkpoint_dir",
        str(CHECKPOINT),
        "--stage_1",
        "ai2v",
        "--input_json",
        str(job_json),
        "--resolution",
        RESOLUTION,
        "--num_segments",
        str(segments),
        "--output_dir",
        str(generated_dir),
        "--ref_img_index",
        "0",
        "--mask_frame_range",
        "3",
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO)
    environment["LONGCAT_SEED"] = str(SEED)
    environment["PYTHONUNBUFFERED"] = "1"
    log_path = work / "render.log"

    with GPU_LOCK, log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=str(REPO),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        raise HTTPException(status_code=500, detail="LongCat render failed: " + " | ".join(tail))

    generated = generated_dir / ("final_video.mp4" if segments > 1 else "segment_001.mp4")
    if not generated.exists():
        raise HTTPException(status_code=500, detail="LongCat did not create the expected MP4")

    temporary = MEDIA_DIR / f".{safe_id}.part.mp4"
    # Explicit stream mapping avoids selecting the per-segment temporary audio.
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-v",
            "warning",
            "-i",
            str(generated),
            "-i",
            str(normalized_audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(temporary),
        ],
        check=True,
    )
    temporary.replace(final_path)
    return {
        "provider": "longcat_avatar_15_lowmem",
        "model": MODEL_ID,
        "video_url": f"/v1/avatar/media/{final_path.name}",
        "cached": False,
        "render_ms": round((time.perf_counter() - started) * 1000),
    }


@app.get("/v1/avatar/media/{filename}")
def media(filename: str, authorization: str | None = Header(default=None)) -> FileResponse:
    _authorize(authorization)
    if Path(filename).name != filename or not filename.endswith(".mp4"):
        raise HTTPException(status_code=404, detail="Video not found")
    path = MEDIA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)
