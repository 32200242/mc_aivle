from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

from .ai import score_counselor_utterance


STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "training_progress.json"
_LOCK = RLock()
REQUIRED_TURNS = 3


def _load() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"sessions": {}}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"sessions": {}}
    except (OSError, json.JSONDecodeError):
        return {"sessions": {}}


def _save(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_PATH)


def mark_started(session: dict[str, Any]) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with _LOCK:
        state = _load()
        state.setdefault("sessions", {}).setdefault(str(session["id"]), {
            "session_id": str(session["id"]),
            "counselor_id": str(session["owner_id"]),
            "scenario_id": str(session["scenario_id"]),
            "status": "active",
            "started_at": now,
            "completed_at": None,
            "elapsed_seconds": 0,
            "turn_count": 0,
        })
        _save(state)


def finish_session(
    session: dict[str, Any], elapsed_seconds: int, turns: list[dict[str, Any]]
) -> dict[str, Any]:
    mark_started(session)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    counselor_messages = [
        str(turn.get("counselor_message", "")).strip()
        for turn in turns
        if str(turn.get("counselor_message", "")).strip()
    ]
    turn_count = len(counselor_messages)
    completed = turn_count >= REQUIRED_TURNS
    pre_scores = score_counselor_utterance(counselor_messages[0]) if counselor_messages else None
    post_scores = score_counselor_utterance(counselor_messages[-1]) if counselor_messages else None
    score_change = (
        int(post_scores["total"]) - int(pre_scores["total"])
        if pre_scores and post_scores else 0
    )
    with _LOCK:
        state = _load()
        progress = state.setdefault("sessions", {}).setdefault(str(session["id"]), {})
        progress.update({
            "status": "completed" if completed else "ended",
            "completed_at": now if completed else None,
            "ended_at": now,
            "elapsed_seconds": max(0, int(elapsed_seconds)),
            "turn_count": turn_count,
            "pre_scores": pre_scores,
            "post_scores": post_scores,
            "score_change": score_change,
        })
        _save(state)
    return {
        "completed": completed,
        "required_turns": REQUIRED_TURNS,
        "turn_count": turn_count,
        "pre_scores": pre_scores,
        "post_scores": post_scores,
        "score_change": score_change,
    }


def progress_summary(counselor_ids: set[str] | None = None) -> dict[str, Any]:
    with _LOCK:
        sessions = [
            dict(item) for item in _load().get("sessions", {}).values() if isinstance(item, dict)
        ]
    if counselor_ids is not None:
        sessions = [item for item in sessions if str(item.get("counselor_id", "")) in counselor_ids]
    started = len(sessions)
    completed = sum(item.get("status") == "completed" for item in sessions)
    completed_changes = [
        int(item.get("score_change", 0)) for item in sessions if item.get("status") == "completed"
    ]
    by_counselor: dict[str, dict[str, int | float]] = {}
    for item in sessions:
        counselor_id = str(item.get("counselor_id", ""))
        if not counselor_id:
            continue
        row = by_counselor.setdefault(counselor_id, {
            "started": 0, "completed": 0, "completion_rate": 0.0,
            "average_turns": 0.0, "average_score_change": 0.0,
        })
        row["started"] = int(row["started"]) + 1
        if item.get("status") == "completed":
            row["completed"] = int(row["completed"]) + 1
    for row in by_counselor.values():
        row["completion_rate"] = round(int(row["completed"]) / int(row["started"]) * 100, 1)
    for counselor_id, row in by_counselor.items():
        counselor_sessions = [item for item in sessions if str(item.get("counselor_id")) == counselor_id]
        counselor_changes = [
            int(item.get("score_change", 0))
            for item in counselor_sessions if item.get("status") == "completed"
        ]
        row["average_turns"] = round(
            sum(int(item.get("turn_count", 0)) for item in counselor_sessions) / len(counselor_sessions), 1
        )
        row["average_score_change"] = round(
            sum(counselor_changes) / len(counselor_changes), 1
        ) if counselor_changes else 0.0
    return {
        "participating_counselors": len(by_counselor),
        "started": started,
        "completed": completed,
        "completion_rate": round(completed / started * 100, 1) if started else 0.0,
        "average_turns": round(
            sum(int(item.get("turn_count", 0)) for item in sessions) / started, 1
        ) if started else 0.0,
        "average_score_change": round(
            sum(completed_changes) / len(completed_changes), 1
        ) if completed_changes else 0.0,
        "by_counselor": by_counselor,
    }
