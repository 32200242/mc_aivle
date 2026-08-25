from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..auth import CounselorUser
from ..schemas import (
    TrainingCompleteRequest,
    TrainingCompletionResult,
    TrainingSessionCreate,
    TrainingSessionView,
    TurnRequest,
)
from ..services.ai import (
    demo_asset_key,
    demo_first_turn,
    generate_turn,
    is_demo_first_question,
)
from ..services.avatar import avatar_is_configured, render_avatar
from ..services.tts import prepare_tts
from ..services.training_progress import finish_session, mark_started
from ..store import store


router = APIRouter(prefix="/training", tags=["training"])
logger = logging.getLogger(__name__)
_demo_media_locks: dict[str, asyncio.Lock] = {}
AVATAR_FALLBACK_MESSAGE = "립싱크 영상을 생성하지 못해 기본 표정과 음성으로 계속합니다."
AVATAR_SYNC_CACHE_VERSION = "longcat15-v1"


@router.post("/sessions", response_model=TrainingSessionView)
def create_session(request: TrainingSessionCreate, user: CounselorUser) -> TrainingSessionView:
    return store.create_training_session(request, user)


@router.post("/sessions/{session_id}/complete", response_model=TrainingCompletionResult)
def complete_session(
    session_id: str,
    request: TrainingCompleteRequest,
    user: CounselorUser,
) -> TrainingCompletionResult:
    session = store.get_training_session(session_id, user)
    if not session:
        raise HTTPException(status_code=404, detail="교육 세션을 찾을 수 없습니다.")
    assessment = finish_session(session, request.elapsed_seconds, store.get_turns(session_id))
    completed_session = store.complete_training_session(
        session_id, user, completed=bool(assessment["completed"])
    )
    if completed_session is None:
        raise HTTPException(status_code=404, detail="교육 세션을 찾을 수 없습니다.")
    return TrainingCompletionResult(session=completed_session, **assessment)


async def _prepare_media(session: dict, result, cache_key: str | None = None) -> tuple[dict, dict | None]:
    async def prepare() -> tuple[dict, dict | None]:
        tts = await prepare_tts(
            result.turn_id,
            result.tts_text,
            session.get("persona_id", "lee-jieun"),
            result.emotion,
            result.emotion_intensity,
            cache_key,
        )
        avatar = None
        if avatar_is_configured():
            try:
                avatar_cache_key = f"{cache_key}-{AVATAR_SYNC_CACHE_VERSION}" if cache_key else None
                avatar = await render_avatar(
                    result.turn_id,
                    result.tts_text,
                    result.emotion,
                    tts.get("audio_url"),
                    session.get("persona_id", "lee-jieun"),
                    avatar_cache_key,
                )
            except Exception:
                logger.exception("Avatar rendering failed for turn %s", result.turn_id)
                avatar = {"error": AVATAR_FALLBACK_MESSAGE}
        return tts, avatar

    if not cache_key:
        return await prepare()
    lock = _demo_media_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        return await prepare()


@router.post("/sessions/{session_id}/demo/prewarm")
async def prewarm_demo(session_id: str, user: CounselorUser) -> dict:
    """페이지 진입 직후 시연 첫 응답의 음성과 영상을 백그라운드에서 준비한다."""
    session = store.get_training_session(session_id, user)
    if not session:
        raise HTTPException(status_code=404, detail="교육 세션을 찾을 수 없습니다.")
    if store.get_turns(session_id):
        return {"ready": False, "reason": "session_started"}
    result = demo_first_turn(session)
    key = demo_asset_key(session)
    try:
        tts, avatar = await _prepare_media(session, result, key)
    except Exception:
        logger.exception("Demo media prewarm failed for session %s", session_id)
        # 사전 준비 실패는 실제 첫 턴에서 다시 시도할 수 있도록 세션 자체를 막지 않는다.
        return {"ready": False, "reason": "media_unavailable"}
    return {
        "ready": True,
        "cache_key": key,
        "speech_ready": bool(tts.get("audio_url")),
        "speech_provider": tts.get("provider"),
        "speech_error": tts.get("error"),
        "avatar_ready": bool(avatar and avatar.get("video_url")),
        "avatar_error": avatar.get("error") if avatar else None,
    }


@router.post("/sessions/{session_id}/turns/stream")
async def stream_turn(session_id: str, request: TurnRequest, user: CounselorUser) -> StreamingResponse:
    session = store.get_training_session(session_id, user)
    if not session:
        raise HTTPException(status_code=404, detail="교육 세션을 찾을 수 없습니다.")

    async def events():
        yield _sse("turn.started", {"session_id": session_id})
        history = store.get_turns(session_id)
        mark_started(session)
        cache_key = demo_asset_key(session) if is_demo_first_question(request.counselor_message, history) else None
        try:
            result = await generate_turn(
                request.counselor_message,
                session=session,
                history=history,
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
        if avatar_is_configured():
            yield _sse("avatar.rendering", {
                "turn_id": result.turn_id,
                "emotion": result.emotion,
                "message": "2D 표정과 입모양을 준비하고 있습니다.",
            })
        try:
            tts, avatar = await _prepare_media(session, result, cache_key)
        except Exception:
            logger.exception("Media preparation failed for turn %s", result.turn_id)
            yield _sse("avatar.error", {
                "turn_id": result.turn_id,
                "message": AVATAR_FALLBACK_MESSAGE,
            })
            return
        avatar_ready = bool(
            avatar_is_configured()
            and avatar
            and not avatar.get("error")
            and avatar.get("video_url")
        )
        # Always deliver persona-specific speech. The browser defers it until
        # the muted lip-sync video starts, avoiding autoplay blocks and
        # duplicated audio while preserving male/female voice selection.
        yield _sse("tts.ready", {**tts, "defer_to_avatar": avatar_ready})
        if avatar_is_configured():
            try:
                if not avatar or avatar.get("error"):
                    raise RuntimeError((avatar or {}).get("error") or "표현 서비스가 영상을 반환하지 않았습니다.")
                yield _sse("avatar.ready", avatar)
            except Exception:
                yield _sse("avatar.error", {
                    "turn_id": result.turn_id,
                    "message": AVATAR_FALLBACK_MESSAGE,
                })

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
