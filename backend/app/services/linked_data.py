from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from ..schemas import UserView


STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "linked_session_events.json"
PRIMARY_COUNSELOR_ID = "CNS-SEO-00001"

# The four fully-authored case records are assigned to the primary counselor
# account. The 1,724-person counselor directory remains the account directory;
# additional detailed case records can be connected by extending this mapping
# or replacing it with the production assignment table.
CASE_ASSIGNMENTS = {
    "client-001": PRIMARY_COUNSELOR_ID,
    "client-002": PRIMARY_COUNSELOR_ID,
    "client-003": PRIMARY_COUNSELOR_ID,
    "client-004": PRIMARY_COUNSELOR_ID,
}

_LOCK = RLock()


def assigned_counselor_id(client_id: str) -> str | None:
    try:
        from .client_repository import assigned_counselor_id as stored_counselor_id

        return stored_counselor_id(client_id) or CASE_ASSIGNMENTS.get(client_id)
    except (FileNotFoundError, OSError):
        return CASE_ASSIGNMENTS.get(client_id)


def assigned_client_ids(user: UserView) -> set[str]:
    try:
        from .client_repository import assigned_client_ids as stored_client_ids

        stored = stored_client_ids(user.id if user.role == "counselor" else None)
        if stored:
            return stored
    except (FileNotFoundError, OSError):
        pass
    if user.role != "counselor":
        return set(CASE_ASSIGNMENTS)
    return {client_id for client_id, counselor_id in CASE_ASSIGNMENTS.items() if counselor_id == user.id}


def can_access_client(user: UserView, client_id: str) -> bool:
    return user.role != "counselor" or assigned_counselor_id(client_id) == user.id


def _empty_state() -> dict[str, Any]:
    return {"session_events": {}}


def _load() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _empty_state()
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else _empty_state()
    except (OSError, json.JSONDecodeError):
        return _empty_state()


def _save(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_PATH)


def _counselor_scope(counselor_id: str) -> tuple[str, str]:
    # Lazy import avoids coupling dashboard generation to the event store at
    # module-import time.
    from .operational_data import get_counselor_directory

    counselor = next(
        (
            item
            for item in get_counselor_directory()
            if item["id"] == counselor_id
        ),
        None,
    )
    if not counselor:
        return "", ""
    return str(counselor["center_id"]), str(counselor["region_id"])


def record_session_completion(
    *,
    client_id: str,
    session_number: int,
    participant_count: int,
    completed_at: str,
    service_date: str,
) -> bool:
    """Persist one completed session exactly once.

    Returns True only for the first insert, so retries never double-count the
    completed session or its participant total.
    """

    counselor_id = assigned_counselor_id(client_id)
    if not counselor_id:
        return False
    center_id, region_id = _counselor_scope(counselor_id)
    event_id = f"{client_id}:{session_number}"
    with _LOCK:
        state = _load()
        events = state.setdefault("session_events", {})
        if event_id in events:
            return False
        events[event_id] = {
            "id": event_id,
            "client_id": client_id,
            "session_number": session_number,
            "participant_count": max(1, int(participant_count)),
            "counselor_id": counselor_id,
            "center_id": center_id,
            "region_id": region_id,
            "completed_at": completed_at,
            "date": service_date,
        }
        _save(state)
    return True


def list_session_events() -> list[dict[str, Any]]:
    with _LOCK:
        events = _load().get("session_events", {})
        if not isinstance(events, dict):
            return []
        return [dict(item) for item in events.values() if isinstance(item, dict)]
