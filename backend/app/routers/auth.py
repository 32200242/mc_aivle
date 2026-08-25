from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..auth import CurrentUser, authenticate, issue_token
from ..schemas import (
    LoginRequest,
    LoginResponse,
    RecoveryCenterList,
    RecoveryCounselorList,
    UserView,
)
from ..services.account_recovery import get_recovery_center, list_recovery_centers


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user = authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    return LoginResponse(access_token=issue_token(user), user=user)


@router.get("/recovery/centers", response_model=RecoveryCenterList)
def recovery_centers() -> RecoveryCenterList:
    return RecoveryCenterList(centers=list_recovery_centers())


@router.get("/recovery/counselors", response_model=RecoveryCounselorList)
def recovery_counselors(
    center_id: Annotated[
        str,
        Query(min_length=11, max_length=11, pattern=r"^[Cc][Tt][Rr]-[A-Za-z]{3}-\d{3}$"),
    ],
) -> RecoveryCounselorList:
    center = get_recovery_center(center_id)
    if center is None:
        raise HTTPException(status_code=404, detail="해당 시연용 센터를 찾을 수 없습니다.")
    return RecoveryCounselorList(**center)


@router.get("/me", response_model=UserView)
def me(user: CurrentUser) -> UserView:
    return user
