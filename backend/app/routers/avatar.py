from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..auth import CounselorUser
from ..schemas import AvatarStatus
from ..services.avatar import avatar_status, media_path, media_signature


router = APIRouter(prefix="/avatar", tags=["avatar"])


@router.get("/status", response_model=AvatarStatus)
def get_avatar_status(user: CounselorUser) -> AvatarStatus:
    return AvatarStatus.model_validate(avatar_status())


@router.get("/media/{filename}", include_in_schema=False)
def get_avatar_media(filename: str, signature: str) -> FileResponse:
    path = media_path(filename)
    if path is None or not hmac.compare_digest(signature, media_signature(filename)):
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")
    return FileResponse(path, media_type="video/mp4", headers={"Cache-Control": "no-store"})
