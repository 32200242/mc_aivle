from fastapi import APIRouter, HTTPException

from ..auth import CounselorUser
from ..schemas import AIStatus, CopilotCaseRequest, CopilotRequest, CopilotResult
from ..services.copilot import analyze_copilot
from ..services.llm import provider_status_with_probe
from ..services.linked_data import can_access_client
from ..services.session_workflow import completed_record_evidence, get_workflow
from ..synthetic_cases import build_case_analysis_context, get_client_case, get_session


router = APIRouter(tags=["copilot"])

CRITICAL_QUESTIONNAIRE_ITEMS = {
    "FRPS_17",     # 강압·통제 관련 자기보고
    "FSTRESS_27",  # 폭력·범죄 피해
    "FSTRESS_28",  # 가출·비행·법적 문제
    "FSTRESS_38",  # 가족 내 신체적·언어적 폭력
    "FSTRESS_43",  # 치료가 필요한 심리·정서 문제
    "FSTRESS_44",  # 음주 문제
    "FSTRESS_45",  # 행동중독 관련 일상 어려움
    "DIVORCE_01",
}


@router.get("/ai/status", response_model=AIStatus)
async def ai_status(user: CounselorUser) -> AIStatus:
    return AIStatus.model_validate(await provider_status_with_probe())


@router.post("/copilot/analyze", response_model=CopilotResult)
async def analyze(request: CopilotRequest, user: CounselorUser) -> CopilotResult:
    try:
        return await analyze_copilot(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/copilot/analyze-case", response_model=CopilotResult)
async def analyze_case(request: CopilotCaseRequest, user: CounselorUser) -> CopilotResult:
    case = get_client_case(request.client_id)
    if not case or not can_access_client(user, request.client_id):
        raise HTTPException(status_code=404, detail="내담자 사례를 찾을 수 없습니다.")
    if request.session_number is not None and not any(
        item.number == request.session_number for item in case.sessions
    ):
        raise HTTPException(status_code=404, detail="선택한 회기 기록을 찾을 수 없습니다.")
    session = get_session(case, request.session_number)
    workflow = get_workflow(case.id, len(case.sessions), case.current_session_number)
    allowed_number = workflow.next_session_number or workflow.total_sessions
    if session.number > allowed_number:
        raise HTTPException(status_code=409, detail="이전 회기 기록을 확정해야 선택한 회기를 분석할 수 있습니다.")
    saved_evidence = completed_record_evidence(case.id, session.number)
    evidence_by_number = {
        int(item.split("회기", 1)[0]): item
        for item in saved_evidence
        if item.split("회기", 1)[0].isdigit()
    }
    for item in case.sessions:
        if item.number >= session.number or item.number in evidence_by_number:
            continue
        evidence_by_number[item.number] = (
            f"{item.number}회기 확정 상담기록지: 내담자 보고={item.client_report}; "
            f"상담사 관찰={item.counselor_observation}; 개입={', '.join(item.interventions)}; "
            f"반응={item.client_response}; 다음 계획={item.next_plan}"
        )
    finalized_evidence = [evidence_by_number[number] for number in sorted(evidence_by_number)]
    assessment_evidence = [
        f"{item.code} {item.label}: {item.score:g}/{item.max_score:g}, {item.severity}; {item.interpretation}"
        for item in case.assessments
        if not item.code.startswith("BFI10")
    ]
    assessment_evidence.extend(
        f"{item.item_id} 원응답 {item.response_value}/{item.scale_max}({item.response_label}): "
        f"{item.text} [자기보고·직접 확인 필요]"
        for item in case.questionnaire_responses
        if item.item_id in CRITICAL_QUESTIONNAIRE_ITEMS and _requires_direct_confirmation(
            item.item_id, item.response_value
        )
    )
    prior_session_evidence = finalized_evidence
    analysis_request = CopilotRequest(
        transcript=build_case_analysis_context(case, session, finalized_evidence),
        session_goal=(
            "1회기 전 사전문진 결과 검토"
            if session.number == 1
            else f"{session.number}회기 준비: {session.goal} / " + " / ".join(case.counseling_goals)
        ),
        counselor_note="",
        source_label="사전문진" if session.number == 1 else "선택 사례의 사전문진·완료 회기 기록",
        source_type="synthetic_case",
        client_id=case.id,
        session_number=session.number,
        assessment_evidence=assessment_evidence,
        prior_session_evidence=prior_session_evidence,
    )
    try:
        return await analyze_copilot(analysis_request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _requires_direct_confirmation(item_id: str, response_value: int) -> bool:
    if item_id.startswith("FSTRESS_") or item_id == "DIVORCE_01":
        return response_value > 0
    return response_value >= 4
