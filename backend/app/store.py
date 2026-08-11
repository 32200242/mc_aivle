from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from .schemas import TrainingSessionCreate, TrainingSessionView, UserView
from .personas import get_persona
from .synthetic_cases import client_summaries


CLIENTS = client_summaries()


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.training_sessions: dict[str, dict] = {}
        self.turns: dict[str, list[dict]] = {}

    def create_training_session(self, request: TrainingSessionCreate, user: UserView) -> TrainingSessionView:
        persona = get_persona(request.persona_id)
        session = TrainingSessionView(
            id=f"training-{uuid.uuid4().hex[:12]}",
            scenario_id=request.scenario_id,
            difficulty=request.difficulty,
            goal=request.goal,
            persona_name=persona["name"],
            persona_id=persona["id"],
            persona_gender=persona["gender"],
        )
        with self._lock:
            self.training_sessions[session.id] = {
                **session.model_dump(),
                "owner_id": user.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.turns[session.id] = []
        return session

    def get_training_session(self, session_id: str, user: UserView) -> dict | None:
        with self._lock:
            session = self.training_sessions.get(session_id)
            if not session or session["owner_id"] != user.id:
                return None
            return dict(session)

    def complete_training_session(
        self, session_id: str, user: UserView, *, completed: bool
    ) -> TrainingSessionView | None:
        with self._lock:
            session = self.training_sessions.get(session_id)
            if not session or session["owner_id"] != user.id:
                return None
            session["status"] = "completed" if completed else "ended"
            return TrainingSessionView.model_validate(session)

    def add_turn(self, session_id: str, turn: dict) -> None:
        with self._lock:
            self.turns.setdefault(session_id, []).append(turn)

    def get_turns(self, session_id: str) -> list[dict]:
        with self._lock:
            return list(self.turns.get(session_id, []))


store = MemoryStore()
