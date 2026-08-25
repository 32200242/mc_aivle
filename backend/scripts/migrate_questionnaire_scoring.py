"""Copy the fixed demo database and refresh questionnaire data only.

This preserves client assignments, demographics, appointments, and sessions while
moving the 2013 family questionnaires to their original scoring structures.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.questionnaire import calculate_assessments, generate_responses, questionnaire_items


DEFAULT_SOURCE = PROJECT_ROOT / "backend" / "data" / "counseling_demo.sqlite3"
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "data" / "counseling_demo_v3.sqlite3"


def migrate(source: Path, output: Path) -> dict[str, int]:
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)

    connection = sqlite3.connect(output)
    try:
        items = questionnaire_items()
        connection.executemany(
            """
            UPDATE questionnaire_items
            SET section=?,domain=?,text=?,response_type=?,scale_min=?,scale_max=?,reverse_scored=?,source=?,sort_order=?
            WHERE item_id=?
            """,
            [
                (
                    item["section"], item["domain"], item["text"], item["response_type"],
                    item["scale_min"], item["scale_max"], int(item["reverse_scored"]),
                    item["source"], item["sort_order"], item["item_id"],
                )
                for item in items
            ],
        )
        clients = connection.execute(
            "SELECT id,issue_category,risk_tier FROM clients ORDER BY id"
        ).fetchall()
        response_rows: list[tuple[int, str, str]] = []
        assessment_rows: list[tuple[object, ...]] = []
        client_ids: list[tuple[str]] = []
        for client_id, issue, risk_tier in clients:
            responses = generate_responses(str(client_id), str(issue), str(risk_tier))
            scores = calculate_assessments(responses)
            response_rows.extend((value, str(client_id), item_id) for item_id, value in responses.items())
            client_ids.append((str(client_id),))
            assessment_rows.extend(
                (
                    str(client_id), score["code"], score["label"], score["score"], score["max_score"],
                    score["severity"], score["interpretation"], order,
                )
                for order, score in enumerate(scores, start=1)
            )
            if len(client_ids) >= 500:
                _flush(connection, client_ids, response_rows, assessment_rows)
        _flush(connection, client_ids, response_rows, assessment_rows)
        connection.execute(
            "INSERT OR REPLACE INTO dataset_metadata(key,value) VALUES (?,?)",
            ("questionnaire_scoring_version", json.dumps("family-questionnaires-2013-original-v1")),
        )
        connection.commit()
        connection.execute("PRAGMA optimize")
    finally:
        connection.close()

    return {
        "clients": len(clients),
        "questions": len(items),
        "responses": len(clients) * len(items),
    }


def _flush(
    connection: sqlite3.Connection,
    client_ids: list[tuple[str]],
    response_rows: list[tuple[int, str, str]],
    assessment_rows: list[tuple[object, ...]],
) -> None:
    if not client_ids:
        return
    connection.executemany(
        "UPDATE questionnaire_responses SET response_value=? WHERE client_id=? AND item_id=?",
        response_rows,
    )
    connection.executemany("DELETE FROM assessment_scores WHERE client_id=?", client_ids)
    connection.executemany("INSERT INTO assessment_scores VALUES (?,?,?,?,?,?,?,?)", assessment_rows)
    connection.commit()
    client_ids.clear()
    response_rows.clear()
    assessment_rows.clear()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    counts = migrate(args.source, args.output)
    print(json.dumps({"output": str(args.output.resolve()), **counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
