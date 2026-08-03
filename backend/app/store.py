from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from .schemas import TrainingSessionCreate, TrainingSessionView, UserView
from .synthetic_cases import client_summaries


CLIENTS = client_summaries()


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.training_sessions: dict[str, dict] = {}
        self.turns: dict[str, list[dict]] = {}

    def create_training_session(self, request: TrainingSessionCreate, user: UserView) -> TrainingSessionView:
        session = TrainingSessionView(
            id=f"training-{uuid.uuid4().hex[:12]}",
            scenario_id=request.scenario_id,
            difficulty=request.difficulty,
            goal=request.goal,
            persona_name="이지은 (가명)",
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
        session = self.training_sessions.get(session_id)
        if not session:
            return None
        if user.role not in {"central_admin", "center_admin", "trainer"} and session["owner_id"] != user.id:
            return None
        return session

    def add_turn(self, session_id: str, turn: dict) -> None:
        with self._lock:
            self.turns.setdefault(session_id, []).append(turn)

    def get_turns(self, session_id: str) -> list[dict]:
        with self._lock:
            return list(self.turns.get(session_id, []))


store = MemoryStore()
