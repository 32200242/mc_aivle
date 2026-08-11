from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..questionnaire import calculate_assessments, response_label
from ..schemas import (
    AssessmentScore,
    ClientCase,
    ClientPage,
    ClientSummary,
    CounselingSessionRecord,
    QuestionnaireResponse,
    UserView,
)
from .session_workflow import completed_records, get_workflow
from .service_clock import project_iso_date, project_upcoming_iso_datetime, service_today


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "counseling_demo_v3.sqlite3"
PREPARED_COPILOT_CLIENT_ID = "client-00013"


def database_path() -> Path:
    configured = os.getenv("COUNSELING_DATA_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


def database_ready() -> bool:
    return database_path().is_file()


def _connect() -> sqlite3.Connection:
    path = database_path()
    if not path.is_file():
        raise FileNotFoundError(f"상담 데이터 파일을 찾을 수 없습니다: {path}")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def assigned_counselor_id(client_id: str) -> str | None:
    if not database_ready():
        return None
    with _connect() as connection:
        row = connection.execute(
            "SELECT counselor_id FROM counselor_client_assignments WHERE client_id=? AND status='active'",
            (client_id,),
        ).fetchone()
    return str(row["counselor_id"]) if row else None


def assigned_client_ids(counselor_id: str | None = None) -> set[str]:
    if not database_ready():
        return set()
    sql = "SELECT client_id FROM counselor_client_assignments WHERE status='active'"
    parameters: tuple[Any, ...] = ()
    if counselor_id:
        sql += " AND counselor_id=?"
        parameters = (counselor_id,)
    with _connect() as connection:
        return {str(row["client_id"]) for row in connection.execute(sql, parameters)}


def list_client_page(user: UserView, page: int = 1, page_size: int = 10, query: str = "") -> ClientPage:
    page = max(1, page)
    page_size = max(5, min(50, page_size))
    where = ["a.status='active'"]
    parameters: list[Any] = []
    if user.role == "counselor":
        where.append("a.counselor_id=?")
        parameters.append(user.id)
    normalized_query = query.strip()
    if normalized_query:
        where.append("(c.name LIKE ? OR c.case_code LIKE ? OR c.primary_issue LIKE ?)")
        needle = f"%{normalized_query}%"
        parameters.extend([needle, needle, needle])
    where_sql = " AND ".join(where)
    offset = (page - 1) * page_size
    with _connect() as connection:
        schedule_anchor = _dataset_anchor_date(connection)
        total = int(connection.execute(
            f"SELECT COUNT(*) AS value FROM clients c JOIN counselor_client_assignments a ON a.client_id=c.id WHERE {where_sql}",
            parameters,
        ).fetchone()["value"])
        pages = max(1, math.ceil(total / page_size))
        page = min(page, pages)
        offset = (page - 1) * page_size
        rows = connection.execute(
            f"""
            SELECT c.id,c.case_code,c.name,c.age,c.primary_issue,c.next_session_at,c.current_session_number,c.total_sessions
            FROM clients c
            JOIN counselor_client_assignments a ON a.client_id=c.id
            WHERE {where_sql}
            ORDER BY CASE WHEN c.next_session_at IS NULL THEN 1 ELSE 0 END, c.next_session_at, c.case_code
            LIMIT ? OFFSET ?
            """,
            [*parameters, page_size, offset],
        ).fetchall()
    items = [
        _summary_from_row(row, include_saved_progress=user.role == "counselor", schedule_anchor=schedule_anchor)
        for row in rows
    ]
    return ClientPage(items=items, total=total, page=page, page_size=page_size, pages=pages)


def list_client_summaries(user: UserView) -> list[ClientSummary]:
    # Counselor workloads are 3-18 clients in this data set, so the legacy list
    # endpoint stays lightweight. Administrative screens use the paged endpoint.
    size = 50 if user.role == "counselor" else 10
    return list_client_page(user, page=1, page_size=size).items


def get_client_case(client_id: str) -> ClientCase | None:
    if not database_ready():
        return None
    with _connect() as connection:
        schedule_anchor = _dataset_anchor_date(connection)
        client = connection.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        if not client:
            return None
        response_rows = connection.execute(
            """
            SELECT q.item_id,q.section,q.domain,q.text,q.response_type,q.scale_min,q.scale_max,q.reverse_scored,r.response_value
            FROM questionnaire_responses r
            JOIN questionnaire_items q ON q.item_id=r.item_id
            WHERE r.client_id=?
            ORDER BY q.sort_order
            """,
            (client_id,),
        ).fetchall()
        session_rows = connection.execute(
            "SELECT * FROM counseling_sessions WHERE client_id=? ORDER BY session_number", (client_id,)
        ).fetchall()

    total_sessions = int(client["total_sessions"])
    current_session = int(client["current_session_number"])
    completed, status = _progress(client_id, total_sessions, current_session)
    workflow = get_workflow(client_id, total_sessions, current_session)
    workflow_by_number = {item.session_number: item for item in workflow.sessions}
    saved_records = completed_records(client_id)
    saved_initial = saved_records.get(1, {})
    initial_fields = saved_initial.get("record", {}) if isinstance(saved_initial.get("record"), dict) else {}
    effective_current_session = workflow.next_session_number or total_sessions
    projected_intake = project_iso_date(str(client["intake_date"]), schedule_anchor)
    projected_next_session = _projected_next_session(client, schedule_anchor)
    counseling_period = (
        f"{projected_next_session[:10].replace('-', '.')} 시작 예정"
        if completed == 0 and projected_next_session
        else f"{projected_intake.replace('-', '.')} ~ 진행 중"
    )
    sessions = [
        _session_record(
            row,
            saved_records.get(int(row["session_number"])),
            workflow_by_number[int(row["session_number"])].status == "completed",
            schedule_anchor,
        )
        for row in session_rows
    ]
    if workflow.next_session_number is not None and projected_next_session:
        appointment_date = projected_next_session[:10]
        sessions = [
            item.model_copy(update={"date": appointment_date})
            if item.number == effective_current_session else item
            for item in sessions
        ]
    return ClientCase(
        id=str(client["id"]),
        case_code=str(client["case_code"]),
        name=str(client["name"]),
        age=int(client["age"]),
        gender=str(client["gender"]),
        occupation=str(client["occupation"]),
        status=status,
        session_count=completed,
        primary_issue=str(initial_fields.get("내담자 호소문제(주제)") or client["primary_issue"]),
        next_session_at=projected_next_session,
        synthetic=True,
        intake_date=projected_intake,
        counseling_period=counseling_period,
        referral_source=str(client["referral_source"]),
        family_composition=str(initial_fields.get("가계도·가족관계 참고사항") or client["family_composition"]),
        relationship_context=str(client["relationship_context"]),
        presenting_problem=str(initial_fields.get("내담자 호소문제(주제)") or client["presenting_problem"]),
        counseling_goals=(
            [str(initial_fields["상담목표(내담자와 합의된 목표)"])]
            if initial_fields.get("상담목표(내담자와 합의된 목표)")
            else _json_list(client["counseling_goals"])
        ),
        protective_factors=_json_list(client["protective_factors"]),
        risk_notes=_json_list(client["risk_notes"]),
        assessments=[AssessmentScore.model_validate(item) for item in calculate_assessments({
            str(row["item_id"]): int(row["response_value"]) for row in response_rows
        })],
        questionnaire_responses=[
            QuestionnaireResponse(
                item_id=str(row["item_id"]), section=str(row["section"]), domain=str(row["domain"]),
                text=str(row["text"]), response_type=str(row["response_type"]),
                response_value=int(row["response_value"]),
                response_label=response_label(
                    str(row["response_type"]), int(row["response_value"]), str(row["section"])
                ),
                scale_min=int(row["scale_min"]), scale_max=int(row["scale_max"]),
                reverse_scored=bool(row["reverse_scored"]),
            )
            for row in response_rows
        ],
        sessions=sessions,
        current_session_number=effective_current_session,
    )


def dataset_stats() -> dict[str, Any]:
    if not database_ready():
        return {"ready": False, "path": str(database_path())}
    with _connect() as connection:
        metadata = {
            str(row["key"]): _json_value(row["value"])
            for row in connection.execute("SELECT key,value FROM dataset_metadata")
        }
    return {"ready": True, "path": str(database_path()), "size_bytes": database_path().stat().st_size, **metadata}


def _summary_from_row(row: sqlite3.Row, include_saved_progress: bool, schedule_anchor: date) -> ClientSummary:
    current = int(row["current_session_number"])
    total = int(row["total_sessions"])
    if include_saved_progress:
        completed, status = _progress(str(row["id"]), total, current)
    else:
        completed = max(0, current - 1)
        status = "상담 시작 전" if completed == 0 else f"{completed}회기 완료 · {current}회기 준비"
    return ClientSummary(
        id=str(row["id"]), case_code=str(row["case_code"]), name=str(row["name"]), age=int(row["age"]),
        status=status, session_count=completed, primary_issue=str(row["primary_issue"]),
        next_session_at=_projected_next_session(row, schedule_anchor), synthetic=True,
    )


def _projected_next_session(row: sqlite3.Row, schedule_anchor: date) -> str | None:
    if str(row["id"]) == PREPARED_COPILOT_CLIENT_ID:
        return f"{service_today().isoformat()}T09:00:00"
    return project_upcoming_iso_datetime(row["next_session_at"], schedule_anchor)


def _progress(client_id: str, total_sessions: int, current_session: int) -> tuple[int, str]:
    workflow = get_workflow(client_id, total_sessions, current_session)
    completed = sum(item.status == "completed" for item in workflow.sessions)
    if workflow.next_session_number is None:
        return completed, f"{completed}회기 완료"
    if completed == 0:
        return completed, "상담 시작 전"
    return completed, f"{completed}회기 완료 · {workflow.next_session_number}회기 준비"


def _json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value))
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _json_value(value: Any) -> Any:
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def _dataset_anchor_date(connection: sqlite3.Connection) -> date:
    rows = connection.execute(
        "SELECT key,value FROM dataset_metadata WHERE key IN ('generated_at','contains_real_people')"
    ).fetchall()
    metadata = {str(row["key"]): _json_value(row["value"]) for row in rows}
    # Relative projection exists only for the fixed synthetic fixture. A real
    # operational database must retain the appointment timestamps users saved.
    if metadata.get("contains_real_people") is not False or "generated_at" not in metadata:
        return service_today()
    try:
        return datetime.fromisoformat(str(metadata["generated_at"])).date()
    except (TypeError, ValueError):
        return service_today()


def _session_record(
    row: sqlite3.Row,
    saved: dict[str, Any] | None,
    completed: bool,
    schedule_anchor: date,
) -> CounselingSessionRecord:
    base = {
        "id": str(row["id"]),
        "number": int(row["session_number"]),
        "date": str(row["date"]),
        "modality": str(row["modality"]),
        "participants": _json_list(row["participants"]),
        "goal": str(row["goal"]),
        "client_report": str(row["client_report"]) if completed else "",
        "counselor_observation": str(row["counselor_observation"]) if completed else "",
        "interventions": _json_list(row["interventions"]) if completed else [],
        "client_response": str(row["client_response"]) if completed else "",
        "change_since_last": str(row["change_since_last"]) if completed else "",
        "homework": str(row["homework"]) if completed else "",
        "next_plan": str(row["next_plan"]) if completed else "",
        "official_record": None,
    }
    base["date"] = project_iso_date(str(base["date"]), schedule_anchor)
    if not saved:
        return CounselingSessionRecord(**base)

    record = saved.get("record", {}) if isinstance(saved.get("record"), dict) else {}
    soap = saved.get("soap", {}) if isinstance(saved.get("soap"), dict) else {}
    base["date"] = str(saved.get("service_date") or base["date"])
    record_type = "initial_intake" if saved.get("record_type") == "initial_intake" else "session_record"
    base.update({
        "goal": str(
            record.get("상담목표(내담자와 합의된 목표)")
            or record.get("당회기 상담목표")
            or base["goal"]
        ),
        "client_report": "",
        "counselor_observation": "",
        "interventions": [],
        "client_response": "",
        "change_since_last": str(record.get("상담내용") or record.get("상담내용(상담개입)") or ""),
        "homework": "",
        "next_plan": str(record.get("상담계획") or record.get("다음 회기 계획") or ""),
        "official_record": {
            "record_type": record_type,
            "record_label": str(saved.get("record_label") or ("초기상담기록지" if record_type == "initial_intake" else "상담기록지")),
            "fields": {str(key): str(value) for key, value in record.items()},
            "soap": {str(key): str(value) for key, value in soap.items()},
            "finalized_at": str(saved.get("finalized_at") or ""),
        },
    })
    return CounselingSessionRecord(**base)
