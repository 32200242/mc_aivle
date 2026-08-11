from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

from ..record_contract import (
    COUNSELING_METHODS,
    COUNSELING_TYPES,
    INITIAL_FIELDS,
    OFFICIAL_METADATA_FIELDS,
    OFFICIAL_RECORD_FIELD_MAX_LENGTH,
    REQUIRED_INITIAL_FIELDS,
    REQUIRED_SESSION_FIELDS,
    SESSION_FIELDS,
)
from ..schemas import FinalizeSessionRequest, SessionWorkflow


STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "session_workflow.json"
_LOCK = RLock()


def _load() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"clients": {}, "pending_completion_events": {}}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {"clients": {}, "pending_completion_events": {}}
        value.setdefault("clients", {})
        value.setdefault("pending_completion_events", {})
        return value
    except (OSError, json.JSONDecodeError):
        return {"clients": {}, "pending_completion_events": {}}


def _save(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_PATH)


def get_workflow(client_id: str, total_sessions: int, initial_ready_session: int = 1) -> SessionWorkflow:
    with _LOCK:
        state = _load()
        return _workflow_from_state(state, client_id, total_sessions, initial_ready_session)


def _workflow_from_state(
    state: dict[str, Any],
    client_id: str,
    total_sessions: int,
    initial_ready_session: int,
) -> SessionWorkflow:
    completed = state.get("clients", {}).get(client_id, {}).get("completed", {})
    baseline_completed = set(range(1, min(max(initial_ready_session, 1), total_sessions + 1)))
    completed_numbers = baseline_completed | {int(key) for key in completed if str(key).isdigit()}
    next_number = next((number for number in range(1, total_sessions + 1) if number not in completed_numbers), None)
    sessions = []
    for number in range(1, total_sessions + 1):
        saved = completed.get(str(number), {})
        status = "completed" if number in completed_numbers else "ready" if number == next_number else "locked"
        sessions.append({
            "session_number": number,
            "status": status,
            "required_record_type": "initial_intake" if number == 1 else "session_record",
            "required_record_label": "초기상담기록지" if number == 1 else "상담기록지",
            "soap_attached": bool(saved.get("include_soap")),
            "finalized_at": saved.get("finalized_at"),
            "service_date": saved.get("service_date"),
        })
    return SessionWorkflow(
        client_id=client_id,
        next_session_number=next_number,
        total_sessions=total_sessions,
        sessions=sessions,
    )


def completed_record_evidence(client_id: str, before_session: int) -> list[str]:
    with _LOCK:
        completed = _load().get("clients", {}).get(client_id, {}).get("completed", {})
    evidence = []
    for number in range(1, before_session):
        item = completed.get(str(number))
        if not item:
            continue
        record = item.get("record", {})
        label = item.get("record_label", "상담기록지")
        fields = "; ".join(f"{key}={value}" for key, value in record.items() if str(value).strip())
        evidence.append(f"{number}회기 확정 {label}: {fields[:4000]}")
    return evidence


def completed_records(client_id: str) -> dict[int, dict[str, Any]]:
    with _LOCK:
        completed = _load().get("clients", {}).get(client_id, {}).get("completed", {})
    return {
        int(number): dict(item)
        for number, item in completed.items()
        if str(number).isdigit() and isinstance(item, dict)
    }


def finalize_session(
    client_id: str,
    session_number: int,
    total_sessions: int,
    initial_ready_session: int,
    request: FinalizeSessionRequest,
    participant_count: int,
    planned_service_date: str,
    expected_official_fields: dict[str, str],
) -> SessionWorkflow:
    record = request.records.initial_intake if session_number == 1 else request.records.session_record
    required_fields = REQUIRED_INITIAL_FIELDS if session_number == 1 else REQUIRED_SESSION_FIELDS
    missing_fields = [field for field in required_fields if not _meaningful_value(record.get(field))]
    if missing_fields:
        raise ValueError(f"필수 기록 항목을 작성해 주세요: {', '.join(missing_fields)}")
    meaningful = {
        key: str(value).strip()
        for key, value in record.items()
        if _meaningful_value(value)
    }
    if not meaningful:
        label = "초기상담기록지" if session_number == 1 else "상담기록지"
        raise ValueError(f"{label}의 주요 내용을 작성한 후 확정해 주세요.")
    service_date = request.service_date or planned_service_date
    _validate_official_record(
        record,
        session_number=session_number,
        service_date=service_date,
        expected=expected_official_fields,
    )
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with _LOCK:
        state = _load()
        clients = state.setdefault("clients", {})
        client = clients.setdefault(client_id, {"completed": {}})
        completed = client.setdefault("completed", {})
        existing = completed.get(str(session_number))
        workflow = _workflow_from_state(state, client_id, total_sessions, initial_ready_session)
        if not existing and workflow.next_session_number != session_number:
            raise ValueError("현재 작성 가능한 회기가 아닙니다. 이전 회기 기록을 먼저 확정해 주세요.")
        if existing:
            same_request = (
                existing.get("record") == record
                and bool(existing.get("include_soap")) == request.include_soap
                and existing.get("soap", {}) == (request.records.soap if request.include_soap else {})
                and str(existing.get("soap_source_label", "")) == (request.soap_source_label if request.include_soap else "")
                and str(existing.get("service_date", "")) == service_date
            )
            if not same_request:
                raise ValueError("이미 확정된 회기와 다른 내용입니다. 기존 확정 기록을 확인해 주세요.")
        else:
            completed[str(session_number)] = {
                "record_type": "initial_intake" if session_number == 1 else "session_record",
                "record_label": "초기상담기록지" if session_number == 1 else "상담기록지",
                "record": record,
                "include_soap": request.include_soap,
                "soap": request.records.soap if request.include_soap else {},
                "soap_source_label": request.soap_source_label if request.include_soap else "",
                "uncertain_items": request.records.uncertain_items,
                "generation": {
                    "provider": request.records.provider,
                    "model": request.records.model,
                    "mode": request.records.generation_mode,
                    "fallback_reason": request.records.fallback_reason,
                },
                "finalized_at": now,
                "service_date": service_date,
            }
        finalized_at = str((existing or completed[str(session_number)]).get("finalized_at") or now)
        event_id = f"{client_id}:{session_number}"
        state.setdefault("pending_completion_events", {}).setdefault(event_id, {
            "id": event_id,
            "client_id": client_id,
            "session_number": session_number,
            "participant_count": max(1, int(participant_count)),
            "completed_at": finalized_at,
            "service_date": service_date,
        })
        _save(state)
        return _workflow_from_state(state, client_id, total_sessions, initial_ready_session)


def _validate_official_record(
    record: dict[str, str],
    *,
    session_number: int,
    service_date: str,
    expected: dict[str, str],
) -> None:
    narrative_fields = INITIAL_FIELDS if session_number == 1 else SESSION_FIELDS
    allowed_fields = set(OFFICIAL_METADATA_FIELDS) | set(narrative_fields)
    unexpected_fields = sorted(set(record) - allowed_fields)
    if unexpected_fields:
        raise ValueError(f"공식 기록지에 없는 항목을 제거해 주세요: {', '.join(unexpected_fields)}")

    too_long = [
        field for field in narrative_fields
        if len(str(record.get(field, "")).strip()) > OFFICIAL_RECORD_FIELD_MAX_LENGTH
    ]
    if too_long:
        raise ValueError(
            f"공식 기록지 항목은 {OFFICIAL_RECORD_FIELD_MAX_LENGTH}자 이내로 작성해 주세요: {', '.join(too_long)}"
        )

    required_metadata = (
        ("사례번호", "상담자", "상담일자", "상담방법", "상담유형", "내담자1 성명", "내담자1 관계", "내담자1 성별")
        if session_number == 1
        else ("상담자", "내담자", "상담일자", "상담회기", "상담방법", "상담유형")
    )
    missing_metadata = [field for field in required_metadata if not str(record.get(field, "")).strip()]
    if missing_metadata:
        raise ValueError(f"공식 기록지 기본 항목을 작성해 주세요: {', '.join(missing_metadata)}")

    exact_fields = ["상담자"]
    if session_number == 1:
        exact_fields.extend(["사례번호", "내담자1 성명"])
    for field in exact_fields:
        expected_value = str(expected.get(field, "")).strip()
        if expected_value and str(record.get(field, "")).strip() != expected_value:
            raise ValueError(f"{field} 정보가 선택한 사례와 일치하지 않습니다.")

    if session_number > 1 and str(record.get("상담회기", "")).strip() != str(session_number):
        raise ValueError("상담회기가 현재 작성 중인 회기와 일치하지 않습니다.")
    try:
        datetime.strptime(service_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("실제 상담일 형식을 확인해 주세요.") from exc
    if str(record.get("상담일자", "")).strip() != service_date:
        raise ValueError("기록지 상담일자와 실제 상담일이 일치하지 않습니다.")

    method = str(record.get("상담방법", "")).strip()
    if method not in COUNSELING_METHODS:
        raise ValueError("상담방법을 공식 선택지에서 선택해 주세요.")
    counseling_type = str(record.get("상담유형", "")).strip()
    if counseling_type not in COUNSELING_TYPES:
        raise ValueError("상담유형을 공식 선택지에서 선택해 주세요.")

    start_time = str(record.get("상담시작시각", "")).strip()
    end_time = str(record.get("상담종료시각", "")).strip()
    if bool(start_time) != bool(end_time):
        raise ValueError("상담 시작시각과 종료시각을 함께 입력해 주세요.")
    if start_time and end_time:
        try:
            start = datetime.strptime(start_time, "%H:%M")
            end = datetime.strptime(end_time, "%H:%M")
        except ValueError as exc:
            raise ValueError("상담시간 형식을 확인해 주세요.") from exc
        if end <= start:
            raise ValueError("상담 종료시각은 시작시각보다 늦어야 합니다.")

    if session_number == 1:
        invalid_gender_fields = [
            field for field in ("내담자1 성별", "내담자2 성별", "내담자3 성별")
            if str(record.get(field, "")).strip() not in {"", "남", "여"}
        ]
        if invalid_gender_fields:
            raise ValueError(f"성별을 공식 선택지에서 선택해 주세요: {', '.join(invalid_gender_fields)}")


def dispatch_pending_completion_events(event_id: str | None = None) -> int:
    """Deliver durable completion events; failed deliveries remain for retry."""

    with _LOCK:
        pending = dict(_load().get("pending_completion_events", {}))
    if event_id is not None:
        pending = {event_id: pending[event_id]} if event_id in pending else {}

    delivered = 0
    for pending_id, event in pending.items():
        try:
            from .linked_data import list_session_events, record_session_completion

            inserted = record_session_completion(
                client_id=str(event["client_id"]),
                session_number=int(event["session_number"]),
                participant_count=int(event["participant_count"]),
                completed_at=str(event["completed_at"]),
                service_date=str(event.get("service_date") or str(event["completed_at"])[:10]),
            )
            if not inserted and not any(
                str(saved.get("id")) == pending_id for saved in list_session_events()
            ):
                continue
        except Exception:
            continue
        with _LOCK:
            state = _load()
            state.setdefault("pending_completion_events", {}).pop(pending_id, None)
            _save(state)
        delivered += 1
    return delivered


def _meaningful_value(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and "확인 필요" not in text and "추가 입력" not in text and "상담사가 확인" not in text
