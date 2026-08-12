from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DATABASE_PATH = Path("/workspace/backend/data/counseling_demo_v3.sqlite3")
CLIENT_ID = "client-00013"
COUNSELOR_ID = "CNS-SEO-00001"


def main() -> None:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Synthetic demo database not found: {DATABASE_PATH}")

    with sqlite3.connect(DATABASE_PATH) as connection:
        updated = connection.execute(
            """
            UPDATE clients
            SET name=?, age=?, gender=?, occupation=?, primary_issue=?, issue_category=?,
                relationship_context=?, presenting_problem=?, counseling_goals=?,
                protective_factors=?, risk_notes=?, next_session_at=?
            WHERE id=?
            """,
            (
                "황재훈",
                34,
                "남성",
                "회사원",
                "부부 의사소통 및 반복 갈등",
                "부부관계",
                "배우자와 대화를 시작하면 비난과 방어가 반복되고 갈등 후 관계 회복이 늦어지는 순환을 경험함.",
                "생활비와 육아 분담을 둘러싼 반복 갈등을 줄이고 안전한 복구 대화를 연습하고자 상담을 신청함.",
                json.dumps(
                    ["비난 없이 감정과 요청 표현하기", "대화 중단과 재개 규칙 합의하기", "갈등 후 복구 대화 연습하기"],
                    ensure_ascii=False,
                ),
                json.dumps(["상담 참여 의지가 있음", "갈등 후 대화를 다시 시도한 경험이 있음"], ensure_ascii=False),
                json.dumps(["즉각적 위기 징후는 없으나 매 회기 안전 여부 직접 확인"], ensure_ascii=False),
                "2000-01-01T09:00:00",
                CLIENT_ID,
            ),
        ).rowcount
        assignment = connection.execute(
            """
            SELECT 1
            FROM counselor_client_assignments
            WHERE client_id=? AND counselor_id=? AND status='active'
            """,
            (CLIENT_ID, COUNSELOR_ID),
        ).fetchone()
        if updated != 1 or assignment is None:
            raise RuntimeError("Prepared public demo client or counselor assignment is missing")


if __name__ == "__main__":
    main()
