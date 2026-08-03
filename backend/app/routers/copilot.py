from fastapi import APIRouter, HTTPException

from ..auth import TrainingUser
from ..schemas import AIStatus, CopilotCaseRequest, CopilotRequest, CopilotResult
from ..services.copilot import analyze_copilot
from ..services.llm import provider_status_with_probe
from ..synthetic_cases import build_case_analysis_context, get_client_case, get_session


router = APIRouter(tags=["copilot"])


@router.get("/ai/status", response_model=AIStatus)
async def ai_status(user: TrainingUser) -> AIStatus:
    return AIStatus.model_validate(await provider_status_with_probe())


@router.post("/copilot/analyze", response_model=CopilotResult)
async def analyze(request: CopilotRequest, user: TrainingUser) -> CopilotResult:
    try:
        return await analyze_copilot(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/copilot/analyze-case", response_model=CopilotResult)
async def analyze_case(request: CopilotCaseRequest, user: TrainingUser) -> CopilotResult:
    case = get_client_case(request.client_id)
    if not case:
        raise HTTPException(status_code=404, detail="내담자 사례를 찾을 수 없습니다.")
    if request.session_number is not None and not any(
        item.number == request.session_number for item in case.sessions
    ):
        raise HTTPException(status_code=404, detail="선택한 회기 기록을 찾을 수 없습니다.")
    session = get_session(case, request.session_number)
    previous_sessions = [item for item in case.sessions if item.number < session.number]
    analysis_request = CopilotRequest(
        transcript=build_case_analysis_context(case, session),
        session_goal=f"{session.number}회기 준비: {session.goal} / " + " / ".join(case.counseling_goals),
        counselor_note=previous_sessions[-1].counselor_observation if previous_sessions else "",
        source_label="선택 사례의 사전문진·완료 회기 기록",
        source_type="synthetic_case",
        client_id=case.id,
        session_number=session.number,
    )
    try:
        return await analyze_copilot(analysis_request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
