from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException, status

from .config import settings
from .schemas import Role, UserView


DEMO_USERS = {
    "counselor": {
        "password": "demo",
        "user": UserView(
            id="user-counselor-01",
            name="김지현 상담사",
            role="counselor",
            center_id="center-seoul-01",
            center_name="서울 강남구 가족센터",
        ),
    },
    "admin": {
        "password": "demo",
        "user": UserView(
            id="user-admin-01",
            name="홍길동 관리자",
            role="central_admin",
            center_name="한국건강가정진흥원",
        ),
    },
    "trainer": {
        "password": "demo",
        "user": UserView(
            id="user-trainer-01",
            name="이수민 교육담당자",
            role="trainer",
            center_id="center-seoul-01",
            center_name="서울 강남구 가족센터",
        ),
    },
}


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_token(user: UserView, lifetime_seconds: int = 8 * 60 * 60) -> str:
    payload = {
        "sub": user.id,
        "role": user.role,
        "exp": int(time.time()) + lifetime_seconds,
    }
    encoded = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.auth_secret.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}"


def decode_token(token: str) -> dict:
    try:
        encoded, raw_signature = token.split(".", 1)
        expected = hmac.new(settings.auth_secret.encode(), encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(raw_signature)):
            raise ValueError("invalid signature")
        payload = json.loads(_b64decode(encoded))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 인증 토큰입니다.",
        ) from exc


def find_user_by_id(user_id: str) -> UserView | None:
    for item in DEMO_USERS.values():
        user = item["user"]
        if user.id == user_id:
            return user
    return None


def authenticate(username: str, password: str) -> UserView | None:
    item = DEMO_USERS.get(username)
    if not item or not hmac.compare_digest(str(item["password"]), password):
        return None
    return item["user"]


def current_user(authorization: Annotated[str | None, Header()] = None) -> UserView:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    payload = decode_token(authorization.split(" ", 1)[1])
    user = find_user_by_id(str(payload.get("sub", "")))
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user


CurrentUser = Annotated[UserView, Depends(current_user)]


def require_roles(*roles: Role) -> Callable[[UserView], UserView]:
    allowed = set(roles)

    def dependency(user: CurrentUser) -> UserView:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="이 기능을 사용할 권한이 없습니다.")
        return user

    return dependency


AdminUser = Annotated[UserView, Depends(require_roles("central_admin", "center_admin"))]
TrainingUser = Annotated[UserView, Depends(require_roles("counselor", "trainer", "center_admin", "central_admin"))]
