from __future__ import annotations

import asyncio
import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from ..config import PROJECT_ROOT, settings
from ..personas import get_persona


EMOTION_STYLE = {
    "neutral": "차분하고 자연스럽게, 안정된 속도와 보통 음량으로",
    "sad": "슬픔이 은은히 묻어나되 울먹이거나 과장하지 말고, 조금 느리고 부드럽게",
    "angry": "답답함과 억울함이 약간 느껴지되 공격적이거나 큰 소리가 되지 않게, 절제해서",
    "anxious": "불안과 조심스러움이 약간 묻어나고 호흡이 조금 짧게 느껴지되, 당황한 연기는 하지 말고",
    "hurt": "상처받은 마음이 조용히 느껴지되 울음 연기 없이, 부드럽고 낮은 강도로",
    "withdrawn": "감정을 아끼는 듯 담담하고 조심스럽게, 속도를 조금 늦추고 음량을 약간 낮춰",
}
# The scripted first-turn assets are intentionally durable. Once generated,
# they must keep working after Colab disconnects or the laptop restarts.
TTS_CACHE_DIR = PROJECT_ROOT / "backend" / "data" / "demo_media"


def _safe_error_detail(exc: Exception) -> str:
    """Return an actionable TTS error without exposing endpoint credentials."""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        suffix = f": {body[:600]}" if body else ""
        return f"Qwen TTS HTTP {exc.code}{suffix}"
    if isinstance(exc, urllib.error.URLError):
        return f"Qwen TTS 연결 실패: {exc.reason}"
    return f"Qwen TTS {type(exc).__name__}: {str(exc)[:600]}"


def _safe_cache_key(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Za-z0-9_-]", "", value)[:120]
    return normalized or None


def _cached_audio(cache_key: str | None) -> bytes | None:
    safe_key = _safe_cache_key(cache_key)
    if not safe_key:
        return None
    path = TTS_CACHE_DIR / f"{safe_key}.wav"
    return path.read_bytes() if path.exists() else None


def _store_cached_audio(cache_key: str | None, raw: bytes) -> None:
    safe_key = _safe_cache_key(cache_key)
    if not safe_key or not raw:
        return
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = TTS_CACHE_DIR / f".{safe_key}.part"
    temporary.write_bytes(raw)
    temporary.replace(TTS_CACHE_DIR / f"{safe_key}.wav")


def _emotion_instruction(emotion: str, intensity: float) -> tuple[str, float]:
    bounded = max(0.25, min(0.78, float(intensity)))
    strength = "아주 약하게" if bounded < 0.45 else "적당히" if bounded < 0.66 else "분명하지만 절제해서"
    style = EMOTION_STYLE.get(emotion, EMOTION_STYLE["neutral"])
    return f"{style} 말한다. 정서는 {strength} 반영하고 실제 상담 대화처럼 자연스럽게 유지한다.", bounded


def _internal_tts_sync(
    turn_id: str,
    text: str,
    persona_id: str,
    emotion: str,
    emotion_intensity: float,
    cache_key: str | None = None,
) -> dict:
    persona = get_persona(persona_id)
    instruct, bounded_intensity = _emotion_instruction(emotion, emotion_intensity)
    cached = _cached_audio(cache_key)
    if cached:
        return {
            "turn_id": turn_id,
            "text": text,
            "provider": "qwen3_tts_voice_design",
            "persona_id": persona["id"],
            "gender": persona["gender"],
            "voice": persona["tts_speaker"],
            "emotion": emotion,
            "emotion_intensity": bounded_intensity,
            "audio_url": f"data:audio/wav;base64,{base64.b64encode(cached).decode('ascii')}",
            "browser_speech_fallback": False,
            "cached": True,
        }
    payload = json.dumps({
        "text": text,
        "language": "Korean",
        "locale": "ko-KR",
        "voice": persona["tts_speaker"],
        "speaker": persona["tts_speaker"],
        "voice_description": persona["tts_voice_description"],
        "persona_id": persona["id"],
        "gender": persona["gender"],
        "emotion": emotion,
        "emotion_intensity": bounded_intensity,
        "instruct": instruct,
        "cache_key": _safe_cache_key(cache_key),
        "format": "wav",
    }, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "audio/wav, application/json"}
    api_key = settings.internal_tts_api_key or settings.internal_llm_api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(settings.internal_tts_url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=settings.tts_request_timeout) as response:
        content_type = response.headers.get_content_type()
        raw = response.read()
    result = {
        "turn_id": turn_id,
        "text": text,
        "provider": "qwen3_tts_voice_design",
        "persona_id": persona["id"],
        "gender": persona["gender"],
        "voice": persona["tts_speaker"],
        "emotion": emotion,
        "emotion_intensity": bounded_intensity,
    }
    if content_type == "application/json":
        body = json.loads(raw.decode("utf-8"))
        return {**result, "audio_url": body.get("audio_url"), "browser_speech_fallback": not bool(body.get("audio_url"))}
    _store_cached_audio(cache_key, raw)
    encoded = base64.b64encode(raw).decode("ascii")
    return {**result, "audio_url": f"data:{content_type};base64,{encoded}", "browser_speech_fallback": False, "cached": False}


async def prepare_tts(
    turn_id: str,
    text: str,
    persona_id: str = "lee-jieun",
    emotion: str = "neutral",
    emotion_intensity: float = 0.55,
    cache_key: str | None = None,
) -> dict:
    persona = get_persona(persona_id)
    fallback = {
        "turn_id": turn_id,
        "text": text,
        "audio_url": None,
        "browser_speech_fallback": True,
        "provider": "browser",
        "persona_id": persona["id"],
        "gender": persona["gender"],
        "voice": persona["tts_speaker"],
        "emotion": emotion,
        "emotion_intensity": max(0.25, min(0.78, float(emotion_intensity))),
    }
    if not settings.internal_tts_url:
        return fallback
    try:
        return await asyncio.to_thread(
            _internal_tts_sync,
            turn_id,
            text,
            persona["id"],
            emotion,
            emotion_intensity,
            cache_key,
        )
    except Exception as exc:
        # 음성 장애가 교육 턴 전체를 실패시키지 않도록 브라우저 TTS로 격리한다.
        return {**fallback, "error": _safe_error_detail(exc)}
