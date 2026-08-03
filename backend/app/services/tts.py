from __future__ import annotations

import asyncio
import base64
import json
import urllib.request

from ..config import settings


def _internal_tts_sync(turn_id: str, text: str) -> dict:
    payload = json.dumps({
        "text": text,
        "language": "ko-KR",
        "voice": "adult-female-01",
        "format": "mp3",
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        settings.internal_tts_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        content_type = response.headers.get_content_type()
        raw = response.read()
    if content_type == "application/json":
        body = json.loads(raw.decode("utf-8"))
        return {
            "turn_id": turn_id,
            "text": text,
            "audio_url": body.get("audio_url"),
            "browser_speech_fallback": not bool(body.get("audio_url")),
        }
    encoded = base64.b64encode(raw).decode("ascii")
    return {
        "turn_id": turn_id,
        "text": text,
        "audio_url": f"data:{content_type};base64,{encoded}",
        "browser_speech_fallback": False,
    }


async def prepare_tts(turn_id: str, text: str) -> dict:
    if not settings.internal_tts_url:
        return {
            "turn_id": turn_id,
            "text": text,
            "audio_url": None,
            "browser_speech_fallback": True,
        }
    try:
        return await asyncio.to_thread(_internal_tts_sync, turn_id, text)
    except Exception:
        # 음성 장애가 교육 턴 전체를 실패시키지 않도록 브라우저 TTS로 격리한다.
        return {
            "turn_id": turn_id,
            "text": text,
            "audio_url": None,
            "browser_speech_fallback": True,
        }
