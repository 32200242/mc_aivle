from __future__ import annotations

from typing import Any

from ..config import settings
from ..schemas import CopilotRequest, CopilotResult
from .ai import extract_json_object
from .llm import chat_completion, provider_status


def _string_list(value: Any, fallback: list[str], limit: int = 5) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return fallback
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned[:limit] or fallback


def _mock_analysis(request: CopilotRequest) -> CopilotResult:
    transcript = request.transcript
    conflict = any(word in transcript for word in ("싸", "갈등", "화", "비난"))
    anxious = any(word in transcript for word in ("불안", "걱정", "두려", "긴장"))
    issue = "반복되는 비난-방어 상호작용" if conflict else "정서적 욕구와 의사소통 방식 탐색"
    emotion = "불안과 긴장" if anxious else "상처와 답답함"
    first_session = request.source_type in {"synthetic_case", "case_record"} and request.session_number == 1
    status = provider_status()
    return CopilotResult(
        provider=status["provider"], model=status["model"], source_type=request.source_type,
        client_id=request.client_id, session_number=request.session_number,
        summary=(
            "첫 회기 전 사전문진과 접수정보를 종합하면 가족 스트레스와 의사소통 위험 영역을 우선 확인할 필요가 있습니다. 아직 상담사의 직접 관찰과 회기 내 내담자 진술은 없으므로 문진 결과는 초기 가설로만 사용합니다."
            if first_session
            else "제공된 사례 자료에서 내담자는 자신의 어려움이 충분히 수용되지 않는다고 느끼며 관계 안에서 안전하게 표현하고 협력할 방법을 찾고 있습니다."
        ),
        core_issues=(
            ["사전문진에서 확인된 가족 스트레스와 의사소통 취약 영역", "첫 회기에서 문진 응답의 실제 맥락 확인 필요"]
            if first_session else [issue, "감정 표현과 경청 경험의 부족"]
        ),
        observed_emotions=(["직접 관찰 전·첫 회기에서 확인 필요"] if first_session else [emotion]),
        risk_signals=["명시적 위기 단서는 확인되지 않았으나 상담사의 직접 확인이 필요함"],
        recommended_directions=["사실 확인보다 감정과 욕구를 먼저 반영", "반복되는 상호작용 순환을 장면 단위로 탐색"],
        suggested_questions=["그 순간 가장 먼저 느껴진 감정은 무엇이었나요?", "상대가 어떻게 반응해 주기를 바랐나요?"],
        recommended_phrases=["그 상황에서 많이 답답하고 혼자라는 느낌이 드셨군요."],
        avoid_phrases=["누가 더 잘못했는지부터 정해볼게요."],
        soap_draft={
            "S": "사전문진과 접수기록에 기재된 주호소를 첫 회기에서 내담자의 표현으로 재확인할 필요가 있음." if first_session else "내담자는 관계 갈등 상황에서 자신의 말이 수용되지 않는다고 호소함.",
            "O": "첫 회기 전 단계로 상담사의 직접 행동 관찰 자료는 없음. 문진 점수는 자기보고 자료임." if first_session else "완료 회기 기록에서 감정적 긴장과 반복 갈등 표현이 확인됨. 현재 회기에서 직접 재확인 필요.",
            "A": "문진상 가족 스트레스와 관계 위험 영역이 확인되나 임상적 판단은 첫 면담과 추가 사정 후 수행함." if first_session else "의사소통 순환과 정서적 욕구를 추가 탐색할 필요가 있음. 진단적 판단은 하지 않음.",
            "P": ("첫 회기에서 문진 응답의 맥락, 안전, 보호요인과 상담 목표를 공동 확인함." if first_session else request.session_goal + "을 목표로 감정반영과 개방형 질문을 사용함."),
        },
    )


def _copilot_messages(request: CopilotRequest) -> list[dict[str, str]]:
    system = """
너는 가족센터 상담사를 지원하는 한국어 상담 코파일럿이다. 상담사의 전문적 판단을 대체하지 않는다.
제공된 사례 자료에 없는 사실, 진단, 위험을 만들지 않는다. 관찰과 추론을 구분하고 불확실하면 확인 필요라고 쓴다.
자해·타해·학대 등 위기 단서는 risk_signals에 원문 근거와 함께 표시하되 자동 판정하지 않는다.
반드시 유효한 JSON 객체 하나만 출력한다. 첫 문자는 {, 마지막 문자는 }여야 하며 설명·코드펜스·후행 쉼표를 추가하지 않는다.
키는 summary, core_issues, observed_emotions, risk_signals,
recommended_directions, suggested_questions, recommended_phrases, avoid_phrases, soap_draft이다.
soap_draft는 S, O, A, P 문자열을 가진다. 각 목록은 최대 5개다.
""".strip()
    user = f"[회기 목표]\n{request.session_goal}\n\n[추가 상담사 메모]\n{request.counselor_note or '없음'}\n\n[{request.source_label}]\n{request.transcript}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def analyze_copilot(request: CopilotRequest) -> CopilotResult:
    if settings.ai_provider == "mock":
        return _mock_analysis(request)
    raw = await chat_completion(_copilot_messages(request), max_tokens=1400, temperature=0.25)
    data = extract_json_object(raw)
    if not data:
        status = provider_status()
        fallback = _mock_analysis(request)
        return fallback.model_copy(update={
            "provider": status["provider"],
            "model": status["model"],
            "summary": raw.strip()[:2000] or fallback.summary,
        })
    status = provider_status()
    soap = data.get("soap_draft") if isinstance(data.get("soap_draft"), dict) else {}
    return CopilotResult(
        provider=status["provider"], model=status["model"], source_type=request.source_type,
        client_id=request.client_id, session_number=request.session_number,
        summary=str(data.get("summary") or "분석 요약을 생성하지 못했습니다."),
        core_issues=_string_list(data.get("core_issues"), ["추가 탐색 필요"]),
        observed_emotions=_string_list(data.get("observed_emotions"), ["직접 확인 필요"]),
        risk_signals=_string_list(data.get("risk_signals"), ["명시적 단서 없음·상담사 확인 필요"]),
        recommended_directions=_string_list(data.get("recommended_directions"), ["내담자의 정서와 욕구를 추가 탐색"]),
        suggested_questions=_string_list(data.get("suggested_questions"), ["그 순간 어떤 감정이 가장 크게 느껴졌나요?"]),
        recommended_phrases=_string_list(data.get("recommended_phrases"), ["그 경험이 많이 힘드셨겠어요."]),
        avoid_phrases=_string_list(data.get("avoid_phrases"), ["감정이나 의도를 단정하는 표현"]),
        soap_draft={key: str(soap.get(key) or "추가 확인 필요") for key in ("S", "O", "A", "P")},
    )
