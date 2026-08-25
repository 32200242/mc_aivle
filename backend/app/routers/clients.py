import math

from fastapi import APIRouter, HTTPException, Query

from ..auth import CounselorUser
from ..schemas import ClientCase, ClientPage, ClientSummary
from ..services.client_repository import database_ready, list_client_page, list_client_summaries
from ..services.linked_data import assigned_client_ids, can_access_client
from ..services.session_workflow import get_workflow
from ..synthetic_cases import CLIENT_CASES, get_client_case


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientSummary])
def list_clients(user: CounselorUser) -> list[ClientSummary]:
    if database_ready():
        return list_client_summaries(user)
    allowed = assigned_client_ids(user)
    return [_summary_with_progress(case) for case in CLIENT_CASES if case.id in allowed]


@router.get("/page", response_model=ClientPage)
def paged_clients(
    user: CounselorUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=5, le=50),
    q: str = Query(default="", max_length=80),
) -> ClientPage:
    if database_ready():
        return list_client_page(user, page=page, page_size=page_size, query=q)
    allowed = assigned_client_ids(user)
    normalized = q.strip().lower()
    items = [
        _summary_with_progress(case)
        for case in CLIENT_CASES
        if case.id in allowed and (
            not normalized
            or normalized in case.name.lower()
            or normalized in case.case_code.lower()
            or normalized in case.primary_issue.lower()
        )
    ]
    total = len(items)
    pages = max(1, math.ceil(total / page_size))
    page = min(page, pages)
    start = (page - 1) * page_size
    return ClientPage(items=items[start:start + page_size], total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{client_id}", response_model=ClientCase)
def get_client(client_id: str, user: CounselorUser) -> ClientCase:
    client = get_client_case(client_id)
    if not client or not can_access_client(user, client_id):
        raise HTTPException(status_code=404, detail="내담자를 찾을 수 없습니다.")
    completed, status = _progress(client)
    return client.model_copy(update={"session_count": completed, "status": status})


def _progress(case: ClientCase) -> tuple[int, str]:
    workflow = get_workflow(case.id, len(case.sessions), case.current_session_number)
    completed = sum(item.status == "completed" for item in workflow.sessions)
    if workflow.next_session_number is None:
        return completed, f"{completed}회기 완료"
    if completed == 0:
        return completed, "상담 시작 전"
    return completed, f"{completed}회기 완료 · {workflow.next_session_number}회기 준비"


def _summary_with_progress(case: ClientCase) -> ClientSummary:
    completed, status = _progress(case)
    return ClientSummary(
        id=case.id,
        case_code=case.case_code,
        name=case.name,
        age=case.age,
        status=status,
        session_count=completed,
        primary_issue=case.primary_issue,
        next_session_at=case.next_session_at,
        synthetic=case.synthetic,
    )
