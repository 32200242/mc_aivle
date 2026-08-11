from __future__ import annotations

import json
import mimetypes
import uuid
import urllib.error
import urllib.request
from typing import Any

from ..config import settings


def speech_status() -> dict[str, Any]:
    if settings.stt_provider in {"internal_http", "qwen_http"}:
        configured = bool(settings.internal_stt_url)
        reachable: bool | None = None
        detail = "음성 인식 서비스 주소가 비어 있습니다."
        if configured and settings.stt_provider == "qwen_http":
            status_url = settings.internal_stt_url.split("/v1/audio/transcriptions", 1)[0].rstrip("/") + "/v1/speech/status"
            headers = {"Accept": "application/json", "ngrok-skip-browser-warning": "1"}
            api_key = settings.internal_stt_api_key or settings.internal_llm_api_key
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            try:
                request = urllib.request.Request(status_url, headers=headers, method="GET")
                with urllib.request.urlopen(request, timeout=settings.stt_health_timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                reachable = body.get("status") == "ok"
                detail = "음성 인식·합성 서비스가 준비되었습니다." if reachable else "음성 서비스 상태를 확인해 주세요."
            except Exception:
                reachable = False
                detail = "음성 서비스에 연결하지 못했습니다."
        elif configured:
            detail = "내부 음성 인식 서비스가 설정되었습니다."
    else:
        configured = True
        reachable = True
        detail = "프로토타입은 Chrome/Edge 브라우저 음성인식을 사용합니다. 운영에서는 internal_http로 교체하세요."
    return {"provider": settings.stt_provider, "configured": configured, "reachable": reachable, "detail": detail}


def transcribe_internal(filename: str, content: bytes, content_type: str | None) -> str:
    if settings.stt_provider not in {"internal_http", "qwen_http"} or not settings.internal_stt_url:
        raise RuntimeError("내부 STT가 설정되지 않았습니다. 현재 브라우저 STT 모드입니다.")
    boundary = f"----family-center-{uuid.uuid4().hex}"
    mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    body = prefix + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"}
    api_key = settings.internal_stt_api_key or settings.internal_llm_api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(settings.internal_stt_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=settings.stt_request_timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"내부 STT HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"내부 STT 연결 실패: {exc.reason}") from exc
    text = result.get("text") or result.get("transcript")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("내부 STT 응답에 text 또는 transcript가 없습니다.")
    return text.strip()
