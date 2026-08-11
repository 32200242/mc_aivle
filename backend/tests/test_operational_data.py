import re
import sqlite3
from collections import defaultdict
from datetime import date

from backend.app.services.llm import _clamp_max_tokens
from backend.app.services.client_repository import database_path
from backend.app.services.operational_data import build_dashboard, get_operational_dataset
from backend.app.services.queue_planning import build_queue_plan
from backend.scripts.build_counseling_dataset import FEMALE_GIVEN_NAMES, MALE_GIVEN_NAMES


AS_OF = date(2026, 8, 3)


def test_linked_dataset_invariants() -> None:
    dataset = get_operational_dataset(AS_OF)
    regions = dataset["regions"]
    centers = dataset["centers"]
    counselors = dataset["counselors"]
    cohorts = dataset["client_cohorts"]
    daily = dataset["daily_metrics"]

    assert len(regions) == 17
    assert len(centers) == 244
    assert sum(center["center_type"] == "가족센터" for center in centers) == 223
    assert sum(center["center_type"] == "건강가정지원센터" for center in centers) == 9
    assert sum(center["center_type"] == "다문화가족지원센터" for center in centers) == 12
    assert len(counselors) == 1_724
    assert sum(counselor["employment_type"] == "상근" for counselor in counselors) == 403
    assert len(daily) == 244 * 760

    region_ids = {region["id"] for region in regions}
    center_ids = {center["id"] for center in centers}
    counselor_ids = {counselor["id"] for counselor in counselors}
    assert all(center["region_id"] in region_ids for center in centers)
    assert all(counselor["center_id"] in center_ids for counselor in counselors)
    assert all(cohort["counselor_id"] in counselor_ids for cohort in cohorts)
    assert all(row["center_id"] in center_ids for row in daily)


def test_counselor_display_names_are_realistic_and_unique_within_center() -> None:
    counselors = get_operational_dataset(AS_OF)["counselors"]
    names_by_center: dict[str, list[str]] = defaultdict(list)

    for counselor in counselors:
        display_name = counselor["display_name"]
        assert re.fullmatch(r"[가-힣]{3}(?:\([2-9][0-9]*\))?", display_name)
        names_by_center[counselor["center_id"]].append(display_name)

    assert all(len(names) == len(set(names)) for names in names_by_center.values())


def test_counseling_cases_match_name_gender_and_use_couple_focus() -> None:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    rows = connection.execute("SELECT id,name,gender,primary_issue FROM clients").fetchall()
    female_names = set(FEMALE_GIVEN_NAMES)
    male_names = set(MALE_GIVEN_NAMES)

    assert len(rows) == 14_143
    assert sum(row["gender"] == "여성" for row in rows) == 8_142
    assert sum(row["gender"] == "남성" for row in rows) == 6_001
    assert all("부부" in row["primary_issue"] for row in rows)
    for row in rows:
        if row["id"] in {"client-001", "client-002", "client-003", "client-004"}:
            continue
        given_name = row["name"][1:]
        expected = female_names if row["gender"] == "여성" else male_names
        assert given_name in expected


def test_dashboard_rollup_and_forecast_contract() -> None:
    dashboard = build_dashboard(days=365, as_of=AS_OF)
    assert dashboard["center_count"] == 244
    assert dashboard["counselor_count"] == 1_724
    assert len(dashboard["regions"]) == 17
    assert len(dashboard["forecast"]) == 28
    assert dashboard["model"]["selected_model"] == dashboard["model"]["leaderboard"][0]["model"]
    assert dashboard["model"]["cv_folds"] == 3
    assert dashboard["model"]["validation_days"] == 28
    assert abs(sum(dashboard["model"]["ensemble_weights"].values()) - 1.0) < 0.001
    assert dashboard["queue"]["pressure_level"] in {"안정", "주의", "높음"}
    assert dashboard["queue"]["recommended_additional_daily_slots"] >= 0
    assert 60 <= dashboard["pre_post_completion_rate"] <= 85
    assert 3.5 <= dashboard["satisfaction"] <= 4.5
    assert all(point["lower"] <= point["predicted_sessions"] <= point["upper"] for point in dashboard["forecast"])

    seoul = build_dashboard(region_id="SEO", days=30, as_of=AS_OF)
    assert seoul["scope"]["type"] == "region"
    assert all(center["region_id"] == "SEO" for center in seoul["centers"])


def test_saved_dashboard_dates_move_with_requested_as_of() -> None:
    shifted_as_of = date(2026, 8, 6)
    dashboard = build_dashboard(days=365, as_of=shifted_as_of)

    assert dashboard["data_as_of"] == shifted_as_of.isoformat()
    assert dashboard["trend"][-1]["date"] == shifted_as_of.isoformat()
    assert dashboard["forecast"][0]["date"] == "2026-08-07"
    assert dashboard["forecast"][-1]["date"] == "2026-09-03"


def test_queue_plan_includes_existing_backlog_and_clearance_time() -> None:
    plan = build_queue_plan(
        forecast_sessions=[10.0] * 28,
        counselor_count=10,
        daily_slot_capacity=20.0,
        current_waitlist=100,
    )

    assert plan["current_waitlist"] == 100
    assert plan["expected_queue_sessions"] >= 100
    assert 5 <= plan["expected_wait_days"] < 6
    assert plan["backlog_clearance_days"] == 10
    assert plan["projected_backlog_after_horizon"] == 0


def test_midm_output_limit_contract() -> None:
    assert _clamp_max_tokens(1_800) <= 1_600
