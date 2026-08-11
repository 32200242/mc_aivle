from __future__ import annotations

import asyncio

from fastapi import APIRouter, Header, HTTPException, Request

from ..auth import CounselorUser
from ..schemas import SpeechStatus, SpeechTranscript
from ..services.stt import speech_status, transcribe_internal


router = APIRouter(prefix="/speech", tags=["speech"])


@router.get("/status", response_model=SpeechStatus)
def get_speech_status(user: CounselorUser) -> SpeechStatus:
    return SpeechStatus.model_validate(speech_status())


@router.post("/transcribe", response_model=SpeechTranscript)
async def transcribe(
    request: Request,
    user: CounselorUser,
    x_filename: str = Header(default="speech.webm"),
) -> SpeechTranscript:
    content = await request.body()
    if not content or len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="음성 파일은 25MB 이하여야 합니다.")
    try:
        text = await asyncio.to_thread(
            transcribe_internal, x_filename, content, request.headers.get("content-type")
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SpeechTranscript(text=text, provider=speech_status()["provider"])
