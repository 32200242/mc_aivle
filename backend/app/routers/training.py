from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..auth import TrainingUser
from ..schemas import TrainingSessionCreate, TrainingSessionView, TurnRequest
from ..services.ai import generate_turn
from ..services.tts import prepare_tts
from ..store import store


router = APIRouter(prefix="/training", tags=["training"])


@router.post("/sessions", response_model=TrainingSessionView)
def create_session(request: TrainingSessionCreate, user: TrainingUser) -> TrainingSessionView:
    return store.create_training_session(request, user)


@router.post("/sessions/{session_id}/turns/stream")
async def stream_turn(session_id: str, request: TurnRequest, user: TrainingUser) -> StreamingResponse:
    session = store.get_training_session(session_id, user)
    if not session:
        raise HTTPException(status_code=404, detail="교육 세션을 찾을 수 없습니다.")

    async def events():
        yield _sse("turn.started", {"session_id": session_id})
        try:
            result = await generate_turn(
                request.counselor_message,
                session=session,
                history=store.get_turns(session_id),
            )
        except Exception as exc:
            yield _sse("ai.error", {
                "message": str(exc),
                "provider_hint": "AI_PROVIDER와 믿:음 서버 주소를 확인하세요.",
            })
            return
        words = result.response.split(" ")
        for index in range(0, len(words), 4):
            await asyncio.sleep(0.035)
            yield _sse("response.delta", {"text": " ".join(words[index:index + 4]) + " "})
        payload = result.model_dump()
        store.add_turn(session_id, {
            "counselor_message": request.counselor_message,
            **payload,
        })
        yield _sse("turn.completed", payload)
        tts = await prepare_tts(result.turn_id, result.tts_text)
        yield _sse("tts.ready", tts)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
