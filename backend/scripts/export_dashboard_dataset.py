"""Rebuild the linked operational dashboard demo dataset.

The files contain no real people or case records. They are deterministic at a given
``--as-of`` date so the UI, API tests, and validation workbook can be reproduced.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.operational_data import (  # noqa: E402
    ANNUAL_COUNSELING_CONTACTS,
    HISTORY_DAYS,
    SEED,
    TARGET_COUNSELORS,
    TARGET_FULL_TIME_COUNSELORS,
    build_dashboard,
    get_operational_dataset,
)


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], *, compressed: bool = False) -> int:
    materialized = list(rows)
    if not materialized:
        return 0
    opener = gzip.open if compressed else open
    kwargs = {"mode": "wt", "encoding": "utf-8-sig", "newline": ""}
    with opener(path, **kwargs) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def export_dataset(as_of: date, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = get_operational_dataset(as_of)
    dashboard = build_dashboard(days=365, as_of=as_of)
    counts = {
        "regions.csv": _write_csv(output_dir / "regions.csv", dataset["regions"]),
        "centers.csv": _write_csv(output_dir / "centers.csv", dataset["centers"]),
        "counselors.csv": _write_csv(output_dir / "counselors.csv", dataset["counselors"]),
        "client_cohorts.csv": _write_csv(output_dir / "client_cohorts.csv", dataset["client_cohorts"]),
        "daily_center_metrics.csv.gz": _write_csv(
            output_dir / "daily_center_metrics.csv.gz", dataset["daily_metrics"], compressed=True
        ),
        "model_leaderboard.csv": _write_csv(output_dir / "model_leaderboard.csv", dashboard["model"]["leaderboard"]),
    }
    (output_dir / "dashboard_snapshot.json").write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "dataset_kind": "deterministic demonstration data",
        "contains_real_people": False,
        "as_of": as_of.isoformat(),
        "seed": SEED,
        "history_days": HISTORY_DAYS,
        "annual_counseling_contact_anchor": ANNUAL_COUNSELING_CONTACTS,
        "target_counselors": TARGET_COUNSELORS,
        "target_full_time_counselors": TARGET_FULL_TIME_COUNSELORS,
        "selected_forecast_model": dashboard["model"]["selected_model"],
        "validation_days": dashboard["model"]["validation_days"],
        "forecast_engine": dashboard["model"]["engine"],
        "cv_folds": dashboard["model"]["cv_folds"],
        "ensemble_weights": dashboard["model"]["ensemble_weights"],
        "prediction_interval": dashboard["model"]["interval_method"],
        "queue_planning": dashboard["queue"],
        "row_counts": counts,
        "relationships": {
            "regions_to_centers": "regions.id = centers.region_id",
            "centers_to_counselors": "centers.id = counselors.center_id",
            "counselors_to_client_cohorts": "counselors.id = client_cohorts.counselor_id",
            "centers_to_daily_metrics": "centers.id = daily_center_metrics.center_id",
        },
        "limitations": [
            "운영 화면과 집계 로직 검증용이며 실제 기관 실적이 아닙니다.",
            "개인별 임상 위험 또는 상담 성과를 예측하지 않습니다.",
            "실서비스 전 기관·지역 코드와 실적 정의를 운영 데이터 표준에 맞춰 재매핑해야 합니다.",
            "Erlang-C 대기값은 포아송 도착·독립 처리·대기 이탈 없음 가정의 운영계획 근사입니다.",
        ],
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "dashboard_demo",
    )
    args = parser.parse_args()
    metadata = export_dataset(date.fromisoformat(args.as_of), args.output.resolve())
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
