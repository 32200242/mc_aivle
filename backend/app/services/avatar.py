from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..config import PROJECT_ROOT, settings


EMOTIONS = {"neutral", "sad", "angry", "anxious", "hurt", "withdrawn"}
PERSONAS_DIR = PROJECT_ROOT / "frontend" / "public" / "personas"
PERSONA_IDS = {"lee-jieun", "kim-minseok"}
MEDIA_DIR = PROJECT_ROOT / "tmp" / "avatar_media"
DEMO_MEDIA_DIR = PROJECT_ROOT / "backend" / "data" / "demo_media"
LONGCAT_MODEL_ID = "meituan-longcat/LongCat-Video-Avatar-1.5"


def avatar_is_configured() -> bool:
    return settings.avatar_provider == "longcat_http" and bool(settings.longcat_avatar_base_url)


def _headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "ngrok-skip-browser-warning": "1",
    }
    if settings.longcat_avatar_api_key:
        headers["Authorization"] = f"Bearer {settings.longcat_avatar_api_key}"
    return headers


def _request_json(path: str, *, payload: dict | None = None, timeout: float) -> dict:
    url = f"{settings.longcat_avatar_base_url}{path}"
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=_headers(),
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace").strip()
            parsed = json.loads(raw)
            detail = parsed.get("detail") if isinstance(parsed, dict) else raw
        except Exception:
            detail = ""
        suffix = f": {str(detail)[:1200]}" if detail else ""
        raise RuntimeError(f"2D 립싱크 서버 HTTP {exc.code}{suffix}") from exc


def avatar_status() -> dict:
    if not avatar_is_configured():
        return {
            "provider": "static_2d",
            "model": None,
            "configured": False,
            "reachable": None,
            "detail": "LongCat 워커는 비활성화되어 있습니다. 감정별 2D 사진과 기존 TTS를 사용합니다.",
            "latency_ms": None,
        }
    started = time.perf_counter()
    try:
        body = _request_json("/v1/avatar/status", timeout=min(10, settings.longcat_avatar_request_timeout))
        reachable = body.get("status") == "ok"
        detail = "LongCat-Video-Avatar 1.5 전용 GPU 워커가 응답 중입니다." if reachable else "LongCat 워커 상태 응답을 확인하세요."
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        reachable = False
        detail = f"2D 립싱크 서버에 연결하지 못했습니다: {exc}"
    return {
        "provider": "longcat_http",
        "model": body.get("model", LONGCAT_MODEL_ID) if reachable else LONGCAT_MODEL_ID,
        "configured": True,
        "reachable": reachable,
        "detail": detail,
        "batch_size": body.get("batch_size") if reachable else None,
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


def _source_image(persona_id: str, emotion: str) -> tuple[str, str]:
    normalized_persona = persona_id if persona_id in PERSONA_IDS else "lee-jieun"
    normalized = emotion if emotion in EMOTIONS else "neutral"
    persona_dir = PERSONAS_DIR / normalized_persona
    candidates = [persona_dir / f"{normalized}.webp", persona_dir / f"{normalized}.png"]
    path = next((candidate for candidate in candidates if candidate.exists()), persona_dir / "neutral.png")
    if not path.exists():
        path = PERSONAS_DIR / "lee-jieun" / "neutral.png"
    mime_type = "image/webp" if path.suffix.lower() == ".webp" else (mimetypes.guess_type(path.name)[0] or "image/png")
    return base64.b64encode(path.read_bytes()).decode("ascii"), mime_type


def _absolute_media_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://", "data:")):
        return value
    return urllib.parse.urljoin(f"{settings.longcat_avatar_base_url}/", value.lstrip("/"))


def media_signature(filename: str) -> str:
    return hmac.new(settings.auth_secret.encode("utf-8"), filename.encode("utf-8"), hashlib.sha256).hexdigest()


def media_path(filename: str) -> Path | None:
    if not filename.endswith(".mp4") or Path(filename).name != filename:
        return None
    for directory in (DEMO_MEDIA_DIR, MEDIA_DIR):
        candidate = directory / filename
        if candidate.exists():
            return candidate
    return None


def _safe_cache_key(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Za-z0-9_-]", "", value)[:120]
    return normalized or None


def _cached_video_payload(cache_key: str | None, turn_id: str, emotion: str, persona_id: str) -> dict | None:
    safe_key = _safe_cache_key(cache_key)
    if not safe_key:
        return None
    filename = f"{safe_key}.mp4"
    path = DEMO_MEDIA_DIR / filename
    if not path.exists():
        return None
    return {
        "turn_id": turn_id,
        "provider": "longcat_avatar_15_prerendered",
        "emotion": emotion,
        "persona_id": persona_id if persona_id in PERSONA_IDS else "lee-jieun",
        "video_url": f"/api/v1/avatar/media/{filename}?signature={media_signature(filename)}",
        "render_ms": 0,
        "cached": True,
    }


def _download_video(url: str, turn_id: str, cache_key: str | None = None) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={**_headers(), "Accept": "video/mp4"}, method="GET")
    with urllib.request.urlopen(request, timeout=settings.longcat_avatar_request_timeout) as response:
        raw = response.read(50 * 1024 * 1024 + 1)
    if not raw or len(raw) > 50 * 1024 * 1024:
        raise RuntimeError("2D 립싱크 영상이 비어 있거나 50MB를 초과했습니다.")
    safe_turn_id = "".join(char for char in turn_id if char.isalnum() or char in "-_")[:80] or "turn"
    safe_cache_key = _safe_cache_key(cache_key)
    filename = f"{safe_cache_key or safe_turn_id}.mp4"
    destination_dir = DEMO_MEDIA_DIR if safe_cache_key else MEDIA_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 24 * 60 * 60
    for old_path in MEDIA_DIR.glob("*.mp4"):
        try:
            if old_path.stat().st_mtime < cutoff:
                old_path.unlink()
        except OSError:
            pass
    temporary = destination_dir / f".{filename}.part"
    temporary.write_bytes(raw)
    temporary.replace(destination_dir / filename)
    return filename, media_signature(filename)


def _render_sync(
    turn_id: str,
    text: str,
    emotion: str,
    audio_url: str | None,
    persona_id: str,
    cache_key: str | None = None,
) -> dict:
    normalized_persona = persona_id if persona_id in PERSONA_IDS else "lee-jieun"
    cached = _cached_video_payload(cache_key, turn_id, emotion, normalized_persona)
    if cached:
        return cached
    image_base64, image_mime_type = _source_image(persona_id, emotion)
    body = _request_json(
        "/v1/avatar/render",
        payload={
            "turn_id": turn_id,
            "text": text,
            "emotion": emotion if emotion in EMOTIONS else "neutral",
            "persona_id": persona_id if persona_id in PERSONA_IDS else "lee-jieun",
            "source_image_base64": image_base64,
            "source_image_mime_type": image_mime_type,
            "audio_url": audio_url,
            "cache_key": _safe_cache_key(cache_key),
        },
        timeout=settings.longcat_avatar_request_timeout,
    )
    remote_video_url = _absolute_media_url(body.get("video_url"))
    if not remote_video_url:
        raise RuntimeError("2D 립싱크 서버가 video_url을 반환하지 않았습니다.")
    filename, signature = _download_video(remote_video_url, turn_id, cache_key)
    return {
        "turn_id": turn_id,
        "provider": body.get("provider", "longcat_avatar_15"),
        "emotion": emotion,
        "persona_id": normalized_persona,
        "video_url": f"/api/v1/avatar/media/{filename}?signature={signature}",
        "render_ms": body.get("render_ms"),
        "cached": bool(body.get("cached")),
    }


async def render_avatar(
    turn_id: str,
    text: str,
    emotion: str,
    audio_url: str | None,
    persona_id: str = "lee-jieun",
    cache_key: str | None = None,
) -> dict:
    return await asyncio.to_thread(_render_sync, turn_id, text, emotion, audio_url, persona_id, cache_key)
