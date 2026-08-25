from fastapi import APIRouter, HTTPException

from ..auth import CurrentUser, authenticate, issue_token
from ..schemas import LoginRequest, LoginResponse, UserView


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user = authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    return LoginResponse(access_token=issue_token(user), user=user)


@router.get("/me", response_model=UserView)
def me(user: CurrentUser) -> UserView:
    return user

