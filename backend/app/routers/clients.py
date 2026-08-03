from fastapi import APIRouter, HTTPException

from ..auth import CurrentUser
from ..schemas import ClientCase, ClientSummary
from ..store import CLIENTS
from ..synthetic_cases import get_client_case


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientSummary])
def list_clients(user: CurrentUser) -> list[ClientSummary]:
    return CLIENTS


@router.get("/{client_id}", response_model=ClientCase)
def get_client(client_id: str, user: CurrentUser) -> ClientCase:
    client = get_client_case(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="내담자를 찾을 수 없습니다.")
    return client
