from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ..config import settings
from ..schemas import IntegratedRecords, RecordGenerateRequest, ReportGenerateRequest, ReportResult
from .ai import extract_json_object
from .llm import chat_completion, provider_status


INITIAL_FIELDS = (
    "호소문제", "상담목표", "가족 및 관계 맥락", "주요 스트레스", "위험 및 보호요인", "초기 평가", "확인 필요 사항",
)
SESSION_FIELDS = (
    "당회기 상담목표", "상담내용", "내담자 보고", "상담사 관찰", "상담개입", "내담자 반응", "과제", "다음 회기 계획",
)
SOAP_FIELDS = ("S", "O", "A", "P")


def _text(value: Any, fallback: str = "추가 확인 필요") -> str:
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)):
        value = "\n".join(f"- {item}" for item in value)
    cleaned = str(value).strip()
    return cleaned or fallback


def _fallback_records(request: RecordGenerateRequest, provider: str, model: str) -> IntegratedRecords:
    source = request.transcript.strip() or request.ocr_text.strip() or request.counselor_note.strip()
    issue = source[:600] if source else "입력된 상담 내용이 없어 직접 확인이 필요함."
    correction = request.manual_correction.strip()
    notes = "\n".join(value for value in (request.counselor_note.strip(), correction) if value)
    initial = {
        "호소문제": issue,
        "상담목표": request.session_goal,
        "가족 및 관계 맥락": request.existing_summary or "대화 및 기존 기록을 통해 추가 확인 필요",
        "주요 스트레스": "입력 자료에서 반복 갈등 및 현재 스트레스 요인을 추가 탐색할 필요가 있음.",
        "위험 및 보호요인": "명시적 위기 단서는 자동 판정하지 않으며 상담사가 직접 확인해야 함.",
        "초기 평가": "제공된 자료를 바탕으로 한 초안이며 진단적 판단이 아님.",
        "확인 필요 사항": "OCR 오인식, 직접 관찰, 위험·보호요인을 원문과 대조해야 함.",
    }
    session = {
        "당회기 상담목표": request.session_goal,
        "상담내용": request.transcript or request.ocr_text or "추가 입력 필요",
        "내담자 보고": request.transcript or "OCR 및 상담사 메모와 구분하여 직접 확인 필요",
        "상담사 관찰": notes or "직접 관찰 내용 미입력",
        "상담개입": "감정반영과 개방형 질문을 사용하여 정서와 욕구를 탐색함.",
        "내담자 반응": "회기 원문을 확인하여 보완 필요",
        "과제": "갈등이 시작되는 장면과 감정 변화를 기록해 보기",
        "다음 회기 계획": "반복 상호작용과 취약 정서를 구체적 장면 단위로 탐색함.",
    }
    soap = {
        "S": request.transcript or request.ocr_text or "내담자 주관적 호소를 추가 입력해야 함.",
        "O": notes or "직접 관찰 정보가 입력되지 않음.",
        "A": "관계 안에서 안전한 의사표현과 반복 상호작용을 추가 평가할 필요가 있음. 진단적 판단은 하지 않음.",
        "P": f"{request.session_goal}을 목표로 감정반영, 개방형 질문 및 다음 회기 계획을 구체화함.",
    }
    uncertain = ["AI 초안은 상담사가 원문과 직접 관찰을 대조한 후 수정·확정해야 합니다."]
    if request.ocr_text:
        uncertain.append("OCR 텍스트의 오인식·누락 여부를 업로드 원본과 대조해야 합니다.")
    return IntegratedRecords(
        provider=provider,
        model=model,
        initial_intake=initial,
        session_record=session,
        soap=soap,
        uncertain_items=uncertain,
        source_summary={
            "상담 대화": "반영됨" if request.transcript else "입력 없음",
            "OCR 기록": "반영됨" if request.ocr_text else "입력 없음",
            "상담사 메모": "반영됨" if notes else "입력 없음",
            "기존 요약": "반영됨" if request.existing_summary else "입력 없음",
        },
    )


def _normalize_records(data: dict[str, Any], fallback: IntegratedRecords) -> IntegratedRecords:
    initial_raw = data.get("initial_intake") or data.get("초기상담기록지") or {}
    session_raw = data.get("session_record") or data.get("상담기록지") or {}
    soap_raw = data.get("soap") or data.get("SOAP") or {}
    if not isinstance(initial_raw, dict) or not isinstance(session_raw, dict) or not isinstance(soap_raw, dict):
        return fallback
    initial = {field: _text(initial_raw.get(field), fallback.initial_intake[field]) for field in INITIAL_FIELDS}
    session = {field: _text(session_raw.get(field), fallback.session_record[field]) for field in SESSION_FIELDS}
    soap = {field: _text(soap_raw.get(field), fallback.soap[field]) for field in SOAP_FIELDS}
    uncertain_raw = data.get("uncertain_items") or data.get("확인 필요 항목") or fallback.uncertain_items
    if isinstance(uncertain_raw, str):
        uncertain_raw = [uncertain_raw]
    uncertain = [_text(item) for item in uncertain_raw] if isinstance(uncertain_raw, list) else fallback.uncertain_items
    sources = data.get("source_summary") if isinstance(data.get("source_summary"), dict) else fallback.source_summary
    return IntegratedRecords(
        provider=fallback.provider, model=fallback.model,
        initial_intake=initial, session_record=session, soap=soap,
        uncertain_items=uncertain[:10] or fallback.uncertain_items,
        source_summary={str(key): _text(value) for key, value in sources.items()},
    )


def _record_messages(request: RecordGenerateRequest) -> list[dict[str, str]]:
    system = f"""
너는 가족센터 상담 기록을 정리하는 한국어 보조 도구다. 상담사의 판단을 대체하지 않는다.
입력에 없는 사실·진단·위험을 만들지 말고 관찰과 추론을 구분한다. 불확실한 항목은 확인 필요라고 표시한다.
OCR은 오인식 가능성이 있으므로 상담 대화와 상담사 메모를 우선한다.
유효한 JSON 객체 하나만 출력한다. 키는 initial_intake, session_record, soap, uncertain_items, source_summary이다.
initial_intake 키: {', '.join(INITIAL_FIELDS)}.
session_record 키: {', '.join(SESSION_FIELDS)}.
soap 키: S, O, A, P. 모든 값은 문자열이다. 설명과 코드펜스를 추가하지 않는다.
""".strip()
    context = request.model_dump()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]


async def generate_records(request: RecordGenerateRequest) -> IntegratedRecords:
    status = provider_status()
    fallback = _fallback_records(request, status["provider"], status["model"])
    if settings.ai_provider == "mock":
        return fallback
    raw = await chat_completion(_record_messages(request), max_tokens=1800, temperature=0.2)
    data = extract_json_object(raw)
    if not data:
        fallback.uncertain_items.append("믿:음 출력이 구조화되지 않아 입력 기반 초안을 표시했습니다.")
        return fallback
    return _normalize_records(data, fallback)


def _fallback_report(request: ReportGenerateRequest, provider: str, model: str) -> ReportResult:
    records = request.records
    session_report = f"""[회기 요약 초안]
- 생성시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- 누적 사례 요약: {request.case_summary or records.initial_intake.get('호소문제', '추가 확인 필요')}
- 이번 회기 변화: {request.session_change or '추가 확인 필요'}
- 상담 목표 달성도: {request.goal_status}
- 다음 회기 예정일: {request.next_date}

[SOAP 요약]
S: {records.soap.get('S', '')}
O: {records.soap.get('O', '')}
A: {records.soap.get('A', '')}
P: {records.soap.get('P', '')}
""".strip()
    closing_report = f"""[중간평가/종결 초안]
- 주요 호소 및 경과: {records.initial_intake.get('호소문제', '추가 확인 필요')}
- 주요 변화: {request.session_change or '추가 확인 필요'}
- 목표 달성 상태: {request.goal_status}
- 후속 계획: {records.session_record.get('다음 회기 계획', '추가 확인 필요')}
- 확인 필요 사항: {'; '.join(records.uncertain_items)}
""".strip()
    return ReportResult(
        provider=provider, model=model,
        session_report=session_report,
        closing_report=closing_report,
        review_notice="자동 생성 초안입니다. 상담사가 원문·직접 관찰·기관 양식을 대조한 후 수정·확정해야 합니다.",
    )


async def generate_report(request: ReportGenerateRequest) -> ReportResult:
    status = provider_status()
    fallback = _fallback_report(request, status["provider"], status["model"])
    if settings.ai_provider == "mock":
        return fallback
    system = """
너는 가족센터 상담 기록으로 회기 요약과 중간평가/종결 초안을 작성한다.
입력에 없는 사실이나 진단을 만들지 않는다. 유효한 JSON 객체 하나만 출력한다.
키는 session_report, closing_report이며 값은 한국어 문자열이다. 설명과 코드펜스를 추가하지 않는다.
""".strip()
    raw = await chat_completion([
        {"role": "system", "content": system},
        {"role": "user", "content": request.model_dump_json()},
    ], max_tokens=1500, temperature=0.2)
    data = extract_json_object(raw)
    if not data:
        return fallback
    return ReportResult(
        provider=status["provider"], model=status["model"],
        session_report=_text(data.get("session_report"), fallback.session_report),
        closing_report=_text(data.get("closing_report"), fallback.closing_report),
        review_notice=fallback.review_notice,
    )
