from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from .demand_forecast import select_and_forecast
from .queue_planning import build_queue_plan


SEED = 20260803
HISTORY_DAYS = 760
ANNUAL_COUNSELING_CONTACTS = 307_035
TARGET_COUNSELORS = 1_724
TARGET_FULL_TIME_COUNSELORS = 403
ISSUE_SHARES = [
    ("부부갈등", 0.3437),
    ("부모-자녀 갈등", 0.2625),
    ("기타 가족관계", 0.3230),
    ("이혼 전후", 0.0450),
    ("개인 정서·위기", 0.0258),
]
MONTH_FACTOR = {1: 0.88, 2: 0.92, 3: 1.08, 4: 1.05, 5: 1.02, 6: 1.01,
                7: 0.94, 8: 0.84, 9: 1.09, 10: 1.08, 11: 1.06, 12: 0.93}
WEEKDAY_FACTOR = [1.24, 1.25, 1.20, 1.18, 1.05, 0.75, 0.33]
SAVED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dashboard_demo"
COUNSELOR_SURNAMES = (
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
)
COUNSELOR_GIVEN_NAMES = (
    "서연", "지우", "수진", "민지", "예은", "하윤", "유진", "소연", "은지", "다은",
    "지현", "혜진", "현정", "주연", "윤서", "민서", "채원", "수빈", "지민", "은서",
    "성민", "준호", "도윤", "지훈", "민석", "현우", "태현", "재현", "동현", "승현",
)


# 2024 integrated-center regional distribution + documented later network expansion.
# population/households: 2023 Population and Housing Census; users: 2022 all-program users.
REGION_SPECS = [
    ("SEO", "서울", "서울특별시", 26, 1, 2, 1, 9_384_512, 4_298_420, 1_165_014, 3, 1),
    ("BUS", "부산", "부산광역시", 10, 0, 1, 1, 3_279_604, 1_480_828, 177_951, 5, 6),
    ("DGU", "대구", "대구광역시", 9, 1, 0, 1, 2_379_188, 1_047_270, 392_715, 5, 5),
    ("INC", "인천", "인천광역시", 9, 1, 0, 1, 3_025_950, 1_282_363, 364_082, 2, 2),
    ("GWJ", "광주", "광주광역시", 5, 0, 0, 0, 1_457_090, 639_311, 142_028, 2, 6),
    ("DJN", "대전", "대전광역시", 3, 1, 0, 0, 1_470_336, 665_786, 73_620, 3, 4),
    ("USN", "울산", "울산광역시", 5, 0, 0, 0, 1_107_432, 467_842, 153_633, 6, 5),
    ("SEJ", "세종", "세종특별자치시", 1, 1, 0, 0, 386_261, 158_757, 239_072, 3, 3),
    ("GYE", "경기", "경기도", 26, 3, 1, 2, 13_815_367, 5_722_843, 1_307_265, 3, 2),
    ("GAN", "강원", "강원특별자치도", 18, 0, 1, 0, 1_528_014, 708_894, 352_937, 4, 2),
    ("CBK", "충북", "충청북도", 11, 0, 0, 0, 1_641_481, 741_403, 248_468, 4, 3),
    ("CNM", "충남", "충청남도", 13, 1, 0, 1, 2_216_332, 987_731, 429_665, 2, 4),
    ("JBK", "전북", "전북특별자치도", 13, 0, 1, 1, 1_768_491, 802_546, 400_331, 2, 5),
    ("JNM", "전남", "전라남도", 22, 0, 0, 1, 1_776_668, 808_812, 705_210, 2, 7),
    ("GBK", "경북", "경상북도", 20, 0, 1, 1, 2_589_880, 1_192_294, 726_369, 5, 4),
    ("GNM", "경남", "경상남도", 19, 1, 1, 1, 3_271_148, 1_436_738, 614_043, 4, 6),
    ("JEJ", "제주", "제주특별자치도", 2, 1, 1, 1, 676_767, 286_325, 75_688, 2, 9),
]


MUNICIPALITIES = {
    "SEO": ["서울", "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구", "동부권"],
    "BUS": ["부산", "강서구", "금정구", "기장군", "남구", "북구", "사상구", "사하구", "수영구", "해운대구"],
    "DGU": ["대구", "중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"],
    "INC": ["인천", "중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군"],
    "GWJ": ["광주", "동구", "서구", "남구", "북구"],
    "DJN": ["대전", "동구", "서구", "유성구"],
    "USN": ["울산", "중구", "남구", "동구", "울주군"],
    "SEJ": ["세종", "조치원"],
    "GYE": ["수원시", "성남시", "고양시", "용인시", "화성시", "부천시", "남양주시", "안산시", "평택시", "안양시", "시흥시", "파주시", "김포시", "의정부시", "광주시", "하남시", "광명시", "군포시", "양주시", "오산시", "이천시", "안성시", "구리시", "의왕시", "포천시", "여주시", "동두천시", "양평군", "가평군"],
    "GAN": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양군"],
    "CBK": ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군", "괴산군", "음성군", "단양군"],
    "CNM": ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군"],
    "JBK": ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군"],
    "JNM": ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"],
    "GBK": ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "울진군"],
    "GNM": ["경남", "창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군", "서부권"],
    "JEJ": ["제주시", "서귀포시", "제주광역"],
}


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _allocate(total: int, weights: list[float], minimum: int = 0) -> list[int]:
    if total < minimum * len(weights):
        raise ValueError("allocation total is below the required minimum")
    result = [minimum] * len(weights)
    remaining = total - sum(result)
    weight_sum = sum(weights) or 1.0
    raw = [remaining * weight / weight_sum for weight in weights]
    floors = [int(value) for value in raw]
    result = [base + add for base, add in zip(result, floors, strict=True)]
    remainder = total - sum(result)
    order = sorted(range(len(weights)), key=lambda index: raw[index] - floors[index], reverse=True)
    for index in order[:remainder]:
        result[index] += 1
    return result


def _assign_counselor_display_names(counselors: list[dict[str, Any]]) -> None:
    """Assign stable Korean names and disambiguate duplicates within each center."""
    name_counts_by_center: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for counselor in sorted(counselors, key=lambda row: str(row["id"])):
        digest = hashlib.sha256(str(counselor["id"]).encode("utf-8")).digest()
        base_name = (
            COUNSELOR_SURNAMES[digest[0] % len(COUNSELOR_SURNAMES)]
            + COUNSELOR_GIVEN_NAMES[digest[1] % len(COUNSELOR_GIVEN_NAMES)]
        )
        center_counts = name_counts_by_center[str(counselor["center_id"])]
        center_counts[base_name] += 1
        occurrence = center_counts[base_name]
        counselor["display_name"] = base_name if occurrence == 1 else f"{base_name}({occurrence})"


def _build_regions() -> list[dict[str, Any]]:
    regions = []
    for spec in REGION_SPECS:
        (region_id, short_name, name, base, expansion, healthy, multicultural,
         population, households, annual_users, map_x, map_y) = spec
        regions.append({
            "id": region_id,
            "name": name,
            "short_name": short_name,
            "family_center_count": base + expansion,
            "healthy_center_count": healthy,
            "multicultural_center_count": multicultural,
            "center_count": base + expansion + healthy + multicultural,
            "population": population,
            "households": households,
            "annual_service_users_2022": annual_users,
            "map_x": map_x,
            "map_y": map_y,
        })
    return regions


def _build_centers(regions: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    population_total = sum(region["population"] for region in regions)
    user_total = sum(region["annual_service_users_2022"] for region in regions)
    centers: list[dict[str, Any]] = []
    for region in regions:
        center_types = (
            ["가족센터"] * region["family_center_count"]
            + ["건강가정지원센터"] * region["healthy_center_count"]
            + ["다문화가족지원센터"] * region["multicultural_center_count"]
        )
        municipalities = MUNICIPALITIES[region["id"]]
        for index, center_type in enumerate(center_types, start=1):
            if center_type == "가족센터":
                municipality = municipalities[min(index - 1, len(municipalities) - 1)]
                name = f"{municipality} 가족센터"
            else:
                legacy_index = index - region["family_center_count"]
                name = f"{region['short_name']} {center_type} {legacy_index}"
            population_share = region["population"] / population_total / region["center_count"]
            user_share = region["annual_service_users_2022"] / user_total / region["center_count"]
            base_weight = 0.45 * population_share + 0.55 * user_share
            demand_factor = rng.lognormvariate(0, 0.18)
            centers.append({
                "id": f"CTR-{region['id']}-{index:03d}",
                "name": name,
                "center_type": center_type,
                "region_id": region["id"],
                "region_name": region["name"],
                "municipality": municipality if center_type == "가족센터" else region["short_name"],
                "throughput_weight": base_weight * demand_factor,
                "demand_index": round(_clip(demand_factor, 0.68, 1.48), 3),
                "quality_score": round(_clip(rng.gauss(82.5, 4.8), 68, 94), 1),
                "opened_year": rng.randint(2006, 2025),
            })
    weight_sum = sum(center["throughput_weight"] for center in centers)
    for center in centers:
        center["throughput_weight"] /= weight_sum
    return centers


def _build_counselors(centers: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    weights = [center["throughput_weight"] for center in centers]
    full_time_counts = _allocate(TARGET_FULL_TIME_COUNSELORS, weights, minimum=1)
    commissioned_counts = _allocate(TARGET_COUNSELORS - TARGET_FULL_TIME_COUNSELORS, weights, minimum=2)
    specialties = [issue for issue, _ in ISSUE_SHARES]
    counselors: list[dict[str, Any]] = []
    for center, full_time_count, commissioned_count in zip(
        centers, full_time_counts, commissioned_counts, strict=True
    ):
        center["full_time_counselors"] = full_time_count
        center["commissioned_counselors"] = commissioned_count
        center["counselor_count"] = full_time_count + commissioned_count
        sequence = 0
        for employment_type, count in (("상근", full_time_count), ("위촉", commissioned_count)):
            for _ in range(count):
                sequence += 1
                tenure_mean = 4.55 if employment_type == "상근" else 5.77
                tenure = round(_clip(rng.gauss(tenure_mean, 2.8), 0.3, 20), 1)
                weekly_capacity = 6 if employment_type == "상근" else 3
                active_clients = max(3, round(rng.gauss(12 if employment_type == "상근" else 7, 2.2)))
                utilization = round(_clip(rng.gauss(71, 10), 38, 98), 1)
                counselors.append({
                    "id": f"CNS-{center['region_id']}-{len(counselors) + 1:05d}",
                    "display_name": "",
                    "center_id": center["id"],
                    "center_name": center["name"],
                    "region_id": center["region_id"],
                    "employment_type": employment_type,
                    "tenure_years": tenure,
                    "weekly_capacity": weekly_capacity,
                    "active_clients": active_clients,
                    "utilization_rate": utilization,
                    "supervisor_eligible": tenure >= 8 and rng.random() < 0.52,
                    "training_completion_rate": round(_clip(rng.gauss(88, 8), 55, 100), 1),
                    "primary_specialty": specialties[(sequence + len(counselors)) % len(specialties)],
                })
        center["active_clients"] = sum(
            counselor["active_clients"]
            for counselor in counselors
            if counselor["center_id"] == center["id"]
        )
    _assign_counselor_display_names(counselors)
    return counselors


def _build_client_cohorts(counselors: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    cohorts: list[dict[str, Any]] = []
    issue_weights = [share for _, share in ISSUE_SHARES]
    for counselor in counselors:
        counts = _allocate(counselor["active_clients"], issue_weights)
        for (issue, _), count in zip(ISSUE_SHARES, counts, strict=True):
            if count <= 0:
                continue
            high = min(count, round(count * _clip(rng.gauss(0.055, 0.018), 0.02, 0.12)))
            monitor = min(count - high, round(count * _clip(rng.gauss(0.18, 0.04), 0.08, 0.30)))
            cohorts.append({
                "counselor_id": counselor["id"],
                "center_id": counselor["center_id"],
                "region_id": counselor["region_id"],
                "issue": issue,
                "client_count": count,
                "standard_count": count - high - monitor,
                "monitor_count": monitor,
                "priority_review_count": high,
            })
    return cohorts


def _daily_capacity(center: dict[str, Any]) -> float:
    return center["full_time_counselors"] * 1.4 + center["commissioned_counselors"] * 0.62


def _build_daily_metrics(
    centers: list[dict[str, Any]], as_of: date, rng: random.Random
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = as_of - timedelta(days=HISTORY_DAYS - 1)
    for day_offset in range(HISTORY_DAYS):
        current = start + timedelta(days=day_offset)
        calendar_factor = WEEKDAY_FACTOR[current.weekday()] * MONTH_FACTOR[current.month]
        for center_index, center in enumerate(centers):
            expected = (
                ANNUAL_COUNSELING_CONTACTS / 365
                * center["throughput_weight"]
                * calendar_factor
            )
            noise = rng.gauss(0, max(0.45, math.sqrt(max(expected, 0.1)) * 0.28))
            sessions = max(0, round(expected + noise))
            no_shows = max(0, min(sessions, round(sessions * _clip(rng.gauss(0.075, 0.02), 0.02, 0.16))))
            capacity = max(1.0, _daily_capacity(center))
            utilization = _clip((sessions + no_shows * 0.35) / capacity * 100, 24, 99)
            waitlist = max(0, round(center["demand_index"] * 2.2 + max(0, utilization - 66) * 0.12 + rng.gauss(0, 1.1)))
            satisfaction_score = _clip(
                3.92 + (center["quality_score"] - 82.5) * 0.018 + rng.gauss(0, 0.08), 3.25, 4.72
            )
            response_count = max(0, round(sessions * 0.42 + rng.gauss(0, 0.35)))
            completed_cases = max(0, round(sessions / 7.4 + rng.gauss(0, 0.22)))
            pre_post_rate = _clip(rng.gauss(0.74, 0.08), 0.45, 0.95)
            pre_post_completed = sum(1 for _ in range(completed_cases) if rng.random() < pre_post_rate)
            rows.append({
                "date": current.isoformat(),
                "center_id": center["id"],
                "region_id": center["region_id"],
                "sessions": sessions,
                "new_intakes": max(0, round(sessions / 6.8 + rng.gauss(0, 0.24))),
                "completed_cases": completed_cases,
                "pre_post_completed": pre_post_completed,
                "no_shows": no_shows,
                "waitlist_end": waitlist,
                "avg_wait_days": round(_clip(1.5 + waitlist / max(1, center["counselor_count"]) * 1.1, 0.5, 18), 1),
                "utilization_rate": round(utilization, 1),
                "satisfaction_responses": response_count,
                "satisfaction_total": round(satisfaction_score * response_count, 3),
                "case_conferences": 1 if current.weekday() == 2 and current.day in range(8, 15) and center_index % 3 == 0 else 0,
                "supervision_hours": 2.0 if current.weekday() == 4 and current.day in range(15, 22) and center_index % 4 == 0 else 0.0,
                "ai_record_minutes": round(_clip(rng.gauss(4.2, 0.55), 2.6, 6.8), 2),
            })
    return rows


def _generate_dataset(as_of_iso: str) -> dict[str, Any]:
    rng = random.Random(SEED)
    as_of = date.fromisoformat(as_of_iso)
    regions = _build_regions()
    centers = _build_centers(regions, rng)
    counselors = _build_counselors(centers, rng)
    client_cohorts = _build_client_cohorts(counselors, rng)
    daily_metrics = _build_daily_metrics(centers, as_of, rng)
    return {
        "as_of": as_of_iso,
        "regions": regions,
        "centers": centers,
        "counselors": counselors,
        "client_cohorts": client_cohorts,
        "daily_metrics": daily_metrics,
    }


def _read_saved_rows(
    filename: str,
    *,
    integer_fields: set[str] | None = None,
    float_fields: set[str] | None = None,
    boolean_fields: set[str] | None = None,
    compressed: bool = False,
) -> list[dict[str, Any]]:
    path = SAVED_DATA_DIR / filename
    opener = gzip.open if compressed else open
    with opener(path, mode="rt", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    integer_fields = integer_fields or set()
    float_fields = float_fields or set()
    boolean_fields = boolean_fields or set()
    for row in rows:
        for field in integer_fields:
            row[field] = int(row[field])
        for field in float_fields:
            row[field] = float(row[field])
        for field in boolean_fields:
            row[field] = row[field].lower() == "true"
    return rows


@lru_cache(maxsize=1)
def _dataset(as_of_iso: str) -> dict[str, Any]:
    """Load the materialized demo once and move only its calendar dates.

    Generating 244 centers x 760 days on every server start made the first
    dashboard request unnecessarily expensive. The checked-in dataset is the
    stable demo fixture; only its relative dates move with the requested date.
    """
    required = [
        "metadata.json", "regions.csv", "centers.csv", "counselors.csv",
        "client_cohorts.csv", "daily_center_metrics.csv.gz",
    ]
    if not all((SAVED_DATA_DIR / filename).exists() for filename in required):
        return _generate_dataset(as_of_iso)

    metadata = json.loads((SAVED_DATA_DIR / "metadata.json").read_text(encoding="utf-8"))
    source_as_of = date.fromisoformat(str(metadata["as_of"]))
    requested_as_of = date.fromisoformat(as_of_iso)
    date_offset = requested_as_of - source_as_of

    regions = _read_saved_rows(
        "regions.csv",
        integer_fields={
            "family_center_count", "healthy_center_count", "multicultural_center_count",
            "center_count", "population", "households", "annual_service_users_2022",
            "map_x", "map_y",
        },
    )
    centers = _read_saved_rows(
        "centers.csv",
        integer_fields={
            "opened_year", "full_time_counselors", "commissioned_counselors",
            "counselor_count", "active_clients",
        },
        float_fields={"throughput_weight", "demand_index", "quality_score"},
    )
    counselors = _read_saved_rows(
        "counselors.csv",
        integer_fields={"weekly_capacity", "active_clients"},
        float_fields={"tenure_years", "utilization_rate", "training_completion_rate"},
        boolean_fields={"supervisor_eligible"},
    )
    _assign_counselor_display_names(counselors)
    client_cohorts = _read_saved_rows(
        "client_cohorts.csv",
        integer_fields={"client_count", "standard_count", "monitor_count", "priority_review_count"},
    )
    daily_metrics = _read_saved_rows(
        "daily_center_metrics.csv.gz",
        integer_fields={
            "sessions", "new_intakes", "completed_cases", "pre_post_completed", "no_shows",
            "waitlist_end", "satisfaction_responses", "case_conferences",
        },
        float_fields={
            "avg_wait_days", "utilization_rate", "satisfaction_total",
            "supervision_hours", "ai_record_minutes",
        },
        compressed=True,
    )
    if date_offset.days:
        shifted_dates = {
            value: (date.fromisoformat(value) + date_offset).isoformat()
            for value in {row["date"] for row in daily_metrics}
        }
        for row in daily_metrics:
            row["date"] = shifted_dates[row["date"]]
    daily_by_center: dict[str, list[dict[str, Any]]] = defaultdict(list)
    daily_by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in daily_metrics:
        daily_by_center[row["center_id"]].append(row)
        daily_by_region[row["region_id"]].append(row)
    return {
        "as_of": as_of_iso,
        "regions": regions,
        "centers": centers,
        "counselors": counselors,
        "client_cohorts": client_cohorts,
        "daily_metrics": daily_metrics,
        "_daily_by_center": dict(daily_by_center),
        "_daily_by_region": dict(daily_by_region),
    }


def get_operational_dataset(as_of: date | None = None) -> dict[str, Any]:
    return _dataset((as_of or date.today()).isoformat())


@lru_cache(maxsize=1)
def get_counselor_directory() -> list[dict[str, Any]]:
    """Load only the account directory, without the 760-day metric table."""

    counselors = _read_saved_rows(
        "counselors.csv",
        integer_fields={"weekly_capacity", "active_clients"},
        float_fields={"tenure_years", "utilization_rate", "training_completion_rate"},
        boolean_fields={"supervisor_eligible"},
    )
    _assign_counselor_display_names(counselors)
    return counselors


def _weighted_average(rows: Iterable[dict[str, Any]], value_key: str, weight_key: str) -> float:
    rows = list(rows)
    total_weight = sum(float(row[weight_key]) for row in rows)
    if total_weight <= 0:
        return 0.0
    return sum(float(row[value_key]) for row in rows) / total_weight


def _aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    if not rows:
        return {
            "sessions": 0, "new_intakes": 0, "completed_cases": 0, "pre_post_completed": 0,
            "no_shows": 0, "waitlist": 0, "avg_wait_days": 0.0, "utilization_rate": 0.0,
            "satisfaction": 0.0, "case_conferences": 0, "supervision_hours": 0.0,
            "ai_record_minutes": 0.0,
        }
    latest_date = ""
    latest_waitlist = 0
    sessions = new_intakes = completed = pre_post_completed = no_shows = 0
    satisfaction_responses = case_conferences = 0
    satisfaction_total = supervision_hours = weighted_ai_minutes = 0.0
    utilization_total = 0.0
    for row in rows:
        row_date = row["date"]
        if row_date > latest_date:
            latest_date = row_date
            latest_waitlist = int(row["waitlist_end"])
        elif row_date == latest_date:
            latest_waitlist += int(row["waitlist_end"])
        row_sessions = int(row["sessions"])
        sessions += row_sessions
        new_intakes += int(row["new_intakes"])
        completed += int(row["completed_cases"])
        pre_post_completed += int(row["pre_post_completed"])
        no_shows += int(row["no_shows"])
        utilization_total += float(row["utilization_rate"])
        responses = int(row["satisfaction_responses"])
        satisfaction_responses += responses
        satisfaction_total += float(row["satisfaction_total"])
        case_conferences += int(row["case_conferences"])
        supervision_hours += float(row["supervision_hours"])
        weighted_ai_minutes += float(row["ai_record_minutes"]) * row_sessions
    return {
        "sessions": sessions,
        "new_intakes": new_intakes,
        "completed_cases": completed,
        "pre_post_completed": pre_post_completed,
        "pre_post_completion_rate": round(pre_post_completed / completed * 100, 1) if completed else 0.0,
        "no_shows": no_shows,
        "waitlist": latest_waitlist,
        "avg_wait_days": round(
            mean(float(row["avg_wait_days"]) for row in rows if row["date"] == latest_date), 1
        ),
        "utilization_rate": round(utilization_total / len(rows), 1),
        "satisfaction": round(satisfaction_total / satisfaction_responses, 2) if satisfaction_responses else 0.0,
        "case_conferences": case_conferences,
        "supervision_hours": round(supervision_hours, 1),
        "ai_record_minutes": round(weighted_ai_minutes / sessions, 2) if sessions else 0.0,
    }


def _percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


def build_dashboard(
    region_id: str | None = None,
    center_id: str | None = None,
    days: int = 90,
    as_of: date | None = None,
) -> dict[str, Any]:
    resolved_as_of = as_of or date.today()
    if not region_id and not center_id and days == 365:
        snapshot = _saved_national_snapshot(resolved_as_of.isoformat())
        if snapshot is not None:
            return _apply_linked_session_events(
                copy.deepcopy(snapshot), region_id=region_id, center_id=center_id
            )
    dashboard = copy.deepcopy(
        _build_dashboard_cached(region_id, center_id, days, resolved_as_of.isoformat())
    )
    return _apply_linked_session_events(dashboard, region_id=region_id, center_id=center_id)


def _apply_linked_session_events(
    dashboard: dict[str, Any],
    *,
    region_id: str | None,
    center_id: str | None,
) -> dict[str, Any]:
    """Overlay newly finalized detailed sessions on the saved operating base."""

    from .session_workflow import dispatch_pending_completion_events
    from .training_progress import progress_summary

    dispatch_pending_completion_events()
    directory = get_counselor_directory()
    scoped_counselor_ids = {
        str(item["id"])
        for item in directory
        if (not region_id or item["region_id"] == region_id)
        and (not center_id or item["center_id"] == center_id)
    }
    training = progress_summary(scoped_counselor_ids)
    dashboard["practice"] = {
        "participating_counselors": training["participating_counselors"],
        "started_sessions": training["started"],
        "completed_sessions": training["completed"],
        "completion_rate": training["completion_rate"],
        "average_turns": training["average_turns"],
        "average_score_change": training["average_score_change"],
    }
    dashboard.setdefault("methodology", {})["practice"] = (
        "AI 상담 실습에서 3회 이상 발화한 세션의 완료 현황과 첫·마지막 발화의 규칙 기반 참고점수 변화; 역량 인증 지표가 아님"
    )
    counselor_progress = training["by_counselor"]
    for counselor in dashboard.get("counselors", []):
        row = counselor_progress.get(counselor["id"])
        counselor["practice_completed_sessions"] = int(row["completed"]) if row else 0
        counselor["practice_score_change"] = float(row["average_score_change"]) if row else 0.0

    queue = dashboard.get("queue", {})
    if "current_waitlist" not in queue:
        dashboard["queue"] = build_queue_plan(
            [float(point["predicted_sessions"]) for point in dashboard.get("forecast", [])],
            counselor_count=int(dashboard.get("counselor_count", 0)),
            daily_slot_capacity=float(queue.get("daily_slot_capacity", 0)),
            current_waitlist=int(dashboard.get("waitlist_count", 0)),
        )

    from .linked_data import list_session_events

    period_start = str(dashboard["period_start"])
    data_as_of = str(dashboard["data_as_of"])
    period_events = [
        event
        for event in list_session_events()
        if period_start <= str(event.get("date", "")) <= data_as_of
    ]
    if not period_events:
        return dashboard

    for region in dashboard.get("regions", []):
        region["sessions"] += sum(
            int(event.get("participant_count", 0))
            for event in period_events
            if event.get("region_id") == region["id"]
        )
    for center in dashboard.get("centers", []):
        center["sessions"] += sum(
            int(event.get("participant_count", 0))
            for event in period_events
            if event.get("center_id") == center["id"]
        )

    scope_events = [
        event
        for event in period_events
        if (not region_id or event.get("region_id") == region_id)
        and (not center_id or event.get("center_id") == center_id)
    ]
    participant_delta = sum(int(event.get("participant_count", 0)) for event in scope_events)
    if not participant_delta:
        return dashboard

    dashboard["counseling_sessions"] += participant_delta
    trend_by_date = {row["date"]: row for row in dashboard.get("trend", [])}
    for event in scope_events:
        row = trend_by_date.get(event.get("date"))
        if row:
            row["sessions"] += int(event.get("participant_count", 0))
    return dashboard


@lru_cache(maxsize=2)
def _saved_national_snapshot(as_of_iso: str) -> dict[str, Any] | None:
    path = SAVED_DATA_DIR / "dashboard_snapshot.json"
    if not path.exists():
        return None
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    _assign_counselor_display_names(snapshot.get("counselors", []))
    source_as_of = date.fromisoformat(snapshot["data_as_of"])
    requested_as_of = date.fromisoformat(as_of_iso)
    offset = requested_as_of - source_as_of
    if offset.days:
        snapshot["data_as_of"] = as_of_iso
        snapshot["period_start"] = (date.fromisoformat(snapshot["period_start"]) + offset).isoformat()
        for row in snapshot["trend"]:
            row["date"] = (date.fromisoformat(row["date"]) + offset).isoformat()
    # 스냅샷의 집계 데이터는 재사용하되 예측 결과는 현재 검증 로직으로 다시 만든다.
    model = select_and_forecast([int(row["sessions"]) for row in snapshot["trend"]], horizon=28)
    predictions = model.pop("forecast")
    lower = model.pop("lower")
    upper = model.pop("upper")
    snapshot["model"] = model
    snapshot["forecast"] = [
        {
            "date": (requested_as_of + timedelta(days=index + 1)).isoformat(),
            "predicted_sessions": prediction,
            "lower": low,
            "upper": high,
        }
        for index, (prediction, low, high) in enumerate(zip(predictions, lower, upper, strict=True))
    ]
    official_2026_users = 304_699
    snapshot.setdefault("service_targets", {
        "year": 2026,
        "family_counseling_users": official_2026_users,
        "family_counseling_satisfaction": 93.0,
        "scope_annual_contact_target": float(official_2026_users),
        "scope_daily_contact_target": round(official_2026_users / 365, 2),
        "scope_monthly_contact_target": round(official_2026_users / 12, 1),
        "source": "한국건강가정진흥원 2025~2029 중장기경영목표",
        "interpretation": "공식 전국 목표를 조회 범위의 최근 누적 상담 참여인원 비중으로 배분한 운영 참고선이며 센터 평가 할당량이 아님",
    })
    if "methodology" in snapshot:
        snapshot["methodology"]["prediction_target"] = (
            "개인 임상결과가 아닌 일별 상담 참여인원; "
            "이전 rolling-origin 구간으로 조정하고 최종 28일에서 독립 평가한 Ridge·Boost·계절모형"
        )
    return snapshot


@lru_cache(maxsize=128)
def _build_dashboard_cached(
    region_id: str | None,
    center_id: str | None,
    days: int,
    as_of_iso: str,
) -> dict[str, Any]:
    data = get_operational_dataset(date.fromisoformat(as_of_iso))
    regions = data["regions"]
    centers = data["centers"]
    counselors = data["counselors"]
    daily = data["daily_metrics"]
    daily_by_center = data.get("_daily_by_center", {})
    daily_by_region = data.get("_daily_by_region", {})
    if not daily_by_center or not daily_by_region:
        daily_by_center = defaultdict(list)
        daily_by_region = defaultdict(list)
        for row in daily:
            daily_by_center[row["center_id"]].append(row)
            daily_by_region[row["region_id"]].append(row)
    cohorts = data["client_cohorts"]
    region_by_id = {region["id"]: region for region in regions}
    center_by_id = {center["id"]: center for center in centers}
    if center_id:
        selected_center = center_by_id.get(center_id)
        if not selected_center:
            raise KeyError("존재하지 않는 센터입니다.")
        region_id = selected_center["region_id"]
    elif region_id and region_id not in region_by_id:
        raise KeyError("존재하지 않는 지역입니다.")

    scope_centers = [
        center for center in centers
        if (not region_id or center["region_id"] == region_id) and (not center_id or center["id"] == center_id)
    ]
    scope_center_ids = {center["id"] for center in scope_centers}
    as_of = date.fromisoformat(data["as_of"])
    period_start = as_of - timedelta(days=days - 1)
    previous_start = period_start - timedelta(days=days)
    if center_id and daily_by_center:
        scope_daily = daily_by_center.get(center_id, [])
    elif region_id and daily_by_region:
        scope_daily = daily_by_region.get(region_id, [])
    else:
        scope_daily = daily
    current_rows = [row for row in scope_daily if row["date"] >= period_start.isoformat()]
    previous_rows = [
        row for row in scope_daily
        if previous_start.isoformat() <= row["date"] < period_start.isoformat()
    ]
    current = _aggregate_rows(current_rows)
    previous = _aggregate_rows(previous_rows)
    scope_counselors = [counselor for counselor in counselors if counselor["center_id"] in scope_center_ids]
    active_clients = sum(counselor["active_clients"] for counselor in scope_counselors)
    training_completion = round(mean(counselor["training_completion_rate"] for counselor in scope_counselors), 1) if scope_counselors else 0.0

    if center_id:
        scope_label = center_by_id[center_id]["name"]
        scope_type = "center"
    elif region_id:
        scope_label = region_by_id[region_id]["name"]
        scope_type = "region"
    else:
        scope_label = "전국"
        scope_type = "national"

    daily_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current_rows:
        daily_grouped[row["date"]].append(row)
    trend = []
    for day, rows in sorted(daily_grouped.items()):
        aggregate = _aggregate_rows(rows)
        trend.append({
            "date": day,
            "sessions": aggregate["sessions"],
            "new_intakes": aggregate["new_intakes"],
            "waitlist": aggregate["waitlist"],
            "utilization_rate": aggregate["utilization_rate"],
            "satisfaction": aggregate["satisfaction"],
        })

    period_rows_by_center = {
        center["id"]: [
            row for row in daily_by_center.get(center["id"], [])
            if row["date"] >= period_start.isoformat()
        ]
        for center in centers
        if not region_id or center["region_id"] == region_id
    }
    period_rows_by_region = {
        region["id"]: [
            row for row in daily_by_region.get(region["id"], [])
            if row["date"] >= period_start.isoformat()
        ]
        for region in regions
    }
    counselors_by_center: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for counselor in counselors:
        counselors_by_center[counselor["center_id"]].append(counselor)

    center_metrics = []
    candidate_centers = [center for center in centers if not region_id or center["region_id"] == region_id]
    for center in candidate_centers:
        metric = _aggregate_rows(period_rows_by_center[center["id"]])
        center_metrics.append({
            "id": center["id"], "name": center["name"], "region_id": center["region_id"],
            "region_name": center["region_name"], "center_type": center["center_type"],
            "counselor_count": center["counselor_count"], "active_clients": center["active_clients"],
            "sessions": metric["sessions"], "waitlist": metric["waitlist"],
            "avg_wait_days": metric["avg_wait_days"], "utilization_rate": metric["utilization_rate"],
            "satisfaction": metric["satisfaction"], "quality_score": center["quality_score"],
            "selected": center["id"] == center_id,
        })
    center_metrics.sort(key=lambda item: (-item["sessions"], item["name"]))

    region_metrics = []
    for region in regions:
        metric = _aggregate_rows(period_rows_by_region[region["id"]])
        region_counselors = [counselor for counselor in counselors if counselor["region_id"] == region["id"]]
        region_metrics.append({
            **region,
            "counselor_count": len(region_counselors),
            "active_clients": sum(counselor["active_clients"] for counselor in region_counselors),
            "sessions": metric["sessions"], "waitlist": metric["waitlist"],
            "utilization_rate": metric["utilization_rate"], "satisfaction": metric["satisfaction"],
            "selected": region["id"] == region_id,
        })

    counselor_rows = []
    for counselor in scope_counselors:
        counselor_rows.append({**counselor})
    counselor_rows.sort(key=lambda item: (-item["utilization_rate"], item["id"]))
    if not center_id:
        counselor_rows = counselor_rows[:24]

    issue_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for cohort in cohorts:
        if cohort["center_id"] in scope_center_ids:
            for key in ("client_count", "standard_count", "monitor_count", "priority_review_count"):
                issue_counts[cohort["issue"]][key] += cohort[key]
    issues = [
        {"issue": issue, **counts}
        for issue, counts in issue_counts.items()
    ]
    issues.sort(key=lambda item: item["client_count"], reverse=True)

    series_by_date: dict[str, int] = defaultdict(int)
    for row in scope_daily:
        series_by_date[row["date"]] += row["sessions"]
    ordered_dates = sorted(series_by_date)
    model = select_and_forecast([series_by_date[day] for day in ordered_dates], horizon=28)
    forecast_dates = [(as_of + timedelta(days=index + 1)).isoformat() for index in range(28)]
    forecast = [
        {"date": day, "predicted_sessions": prediction, "lower": lower, "upper": upper}
        for day, prediction, lower, upper in zip(
            forecast_dates, model.pop("forecast"), model.pop("lower"), model.pop("upper"), strict=True
        )
    ]
    queue_plan = build_queue_plan(
        [point["predicted_sessions"] for point in forecast],
        counselor_count=len(scope_counselors),
        daily_slot_capacity=sum(_daily_capacity(center) for center in scope_centers),
        current_waitlist=int(current["waitlist"]),
    )
    official_2026_users = 304_699
    national_period_rows = [row for row in daily if row["date"] >= period_start.isoformat()]
    national_period_sessions = int(_aggregate_rows(national_period_rows)["sessions"])
    scope_share = float(current["sessions"]) / national_period_sessions if national_period_sessions else 1.0
    scope_annual_target = official_2026_users * scope_share

    return {
        "data_as_of": data["as_of"],
        "period_start": period_start.isoformat(),
        "period_days": days,
        "scope": {"type": scope_type, "id": center_id or region_id, "label": scope_label, "region_id": region_id, "center_id": center_id},
        "center_count": len(scope_centers),
        "counselor_count": len(scope_counselors),
        "active_clients": active_clients,
        "counseling_sessions": current["sessions"],
        "waitlist_count": current["waitlist"],
        "avg_wait_days": current["avg_wait_days"],
        "utilization_rate": current["utilization_rate"],
        "satisfaction": current["satisfaction"],
        "pre_post_completion_rate": current["pre_post_completion_rate"],
        "training_completion_rate": training_completion,
        "ai_report_minutes": current["ai_record_minutes"],
        "changes": {
            "sessions": _percent_change(float(current["sessions"]), float(previous["sessions"])),
            "new_intakes": _percent_change(float(current["new_intakes"]), float(previous["new_intakes"])),
            "waitlist": _percent_change(float(current["waitlist"]), float(previous["waitlist"])),
            "satisfaction": round(float(current["satisfaction"]) - float(previous["satisfaction"]), 2),
        },
        "regions": region_metrics,
        "centers": center_metrics,
        "counselors": counselor_rows,
        "issues": issues,
        "trend": trend,
        "forecast": forecast,
        "model": model,
        "queue": queue_plan,
        "service_targets": {
            "year": 2026,
            "family_counseling_users": official_2026_users,
            "family_counseling_satisfaction": 93.0,
            "scope_annual_contact_target": round(scope_annual_target, 1),
            "scope_daily_contact_target": round(scope_annual_target / 365, 2),
            "scope_monthly_contact_target": round(scope_annual_target / 12, 1),
            "source": "한국건강가정진흥원 2025~2029 중장기경영목표",
            "interpretation": "공식 전국 목표를 조회 범위의 최근 누적 상담 참여인원 비중으로 배분한 운영 참고선이며 센터 평가 할당량이 아님",
        },
        "methodology": {
            "network_total": "한국건강가정진흥원 가족센터 평가지원 사업대상 244개소 기준",
            "regional_allocation": "2024년 통합 가족센터 212개 지역분포를 기준으로 기관유형별 현재 총계에 보정",
            "staffing": "센터당 상근 1.65명·위촉 6.09명 조사와 2024년 212개소 1,497명 실적을 함께 사용",
            "demand": "인구·가구, 2022년 전체 가족센터 이용자, 센터유형을 혼합한 배분 가중치",
            "prediction_target": "개인 임상결과가 아닌 일별 상담 참여인원; 3개 rolling-origin 검증창의 Ridge·Boost·계절모형 앙상블",
            "queue_planning": "예측 상담량과 상담인력별 일일 슬롯을 Erlang-C 대기근사에 입력한 운영계획 참고값",
            "official_targets": "2026년 가족상담 서비스 이용자 304,699명·이용자 만족도 93.0점 목표를 참고하며, 지역·센터 목표선은 최근 누적 상담 참여인원 비중으로 배분한 운영 참고값",
        },
    }
