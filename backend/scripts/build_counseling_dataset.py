"""Build the fixed counselor/client/questionnaire demonstration database.

The generator is intentionally offline and deterministic. The web application
only reads the materialized SQLite file; it never regenerates 14,143 cases on a
page request or invokes an LLM for case creation.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.questionnaire import calculate_assessments, generate_responses, questionnaire_items, stable_seed
from backend.app.synthetic_cases import CLIENT_CASES


DATA_DIR = PROJECT_ROOT / "backend" / "data"
DASHBOARD_DIR = DATA_DIR / "dashboard_demo"
DEFAULT_TARGET = DATA_DIR / "counseling_demo_v3.sqlite3"
PRIMARY_COUNSELOR_ID = "CNS-SEO-00001"
DATASET_SEED = 20260807

SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍"]
FEMALE_GIVEN_NAMES = [
    "민지", "서연", "예진", "하은", "은지", "지영", "소영", "혜진", "다은", "채원",
    "가은", "예은", "수빈", "다현", "민서", "현지", "윤서", "유나", "세아", "아영",
    "나연", "수아", "지혜", "은영", "미영", "선영", "유정", "효진", "연주", "민주",
    "경희", "정은", "혜원", "소연", "다영", "주희", "은경", "지은", "나영", "수정",
]
MALE_GIVEN_NAMES = [
    "도윤", "현우", "지훈", "서준", "민준", "준호", "성민", "태현", "시우", "도현",
    "정우", "재현", "선우", "지호", "승현", "은우", "건우", "민석", "현석", "동현",
    "준혁", "성호", "태준", "상현", "진우", "영호", "재민", "승민", "종현", "민호",
    "정훈", "성진", "기훈", "준영", "현준", "동욱", "승우", "재훈", "경수", "동훈",
]
OCCUPATIONS = ["사무직", "서비스직", "자영업", "전문직", "생산직", "교육직", "보건·의료직", "전업주부", "공공기관 종사자", "프리랜서"]
REFERRALS = ["가족센터 홈페이지 신청", "전화 상담 후 접수", "지역 복지기관 연계", "지인 안내 후 자가 신청", "센터 프로그램 참여 후 연계"]

ISSUE_DETAILS = {
    "부부갈등": {
        "primary": "부부 의사소통 및 반복 갈등",
        "context": "생활 역할과 감정 표현 방식의 차이로 같은 갈등이 반복되고 있다.",
        "problem": "대화를 시작하면 비난과 방어가 이어지고, 갈등 후 관계를 회복하는 데 시간이 오래 걸린다고 보고했다.",
        "goals": ["비난 없이 감정과 요청 표현하기", "갈등 후 복구 대화 연습하기", "역할 기대를 구체적으로 조율하기"],
        "interventions": ["갈등 순환 도식화", "감정 명료화", "I-메시지 연습"],
    },
    "부모-자녀 갈등": {
        "primary": "양육 방식 차이로 인한 부부갈등",
        "context": "자녀의 생활습관과 학업 문제에 대응하는 방식이 달라 부부가 서로의 양육 태도를 비판하는 일이 반복되고 있다.",
        "problem": "훈육 문제를 상의할 때 배우자와 책임 공방으로 번지고, 자녀 앞에서 부부 갈등이 노출되는 것을 걱정한다고 보고했다.",
        "goals": ["부부가 합의할 수 있는 양육 원칙 정하기", "자녀 앞 갈등 노출 줄이기", "배우자의 양육 의도를 확인하며 대화하기"],
        "interventions": ["부부 양육 장면 순서화", "반영적 경청", "공동 양육 원칙 협상"],
    },
    "이혼 전후": {
        "primary": "이혼 전후 부부관계 조정 및 자녀 지원",
        "context": "관계 지속 여부와 향후 생활 계획을 두고 불확실성과 정서적 부담이 이어지고 있다.",
        "problem": "관계 해체에 관한 대화가 감정적 충돌로 이어지고 자녀에게 미칠 영향을 걱정한다고 보고했다.",
        "goals": ["의사결정에 필요한 쟁점 정리하기", "자녀 앞 갈등 노출 줄이기", "공동양육 의사소통 기준 세우기"],
        "interventions": ["의사결정 균형표", "안전 및 위기 확인", "공동양육 대화 구조화"],
    },
    "기타 가족관계": {
        "primary": "돌봄 역할 불균형으로 인한 부부갈등",
        "context": "자녀와 원가족 돌봄, 경제적 책임이 한쪽 배우자에게 집중되면서 부부 사이의 서운함과 정서적 거리가 커졌다.",
        "problem": "배우자에게 도움을 요청하면 서로의 기여를 비교하는 다툼으로 이어져 돌봄과 휴식 시간을 협의하기 어렵다고 보고했다.",
        "goals": ["부부가 돌봄 부담을 구체적으로 공유하기", "비난 없는 도움 요청 문장 연습하기", "부부 역할과 휴식 시간을 재조정하기"],
        "interventions": ["부부 자원 지도", "욕구 구체화", "돌봄 역할 재협상"],
    },
}


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE dataset_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE questionnaire_items (
    item_id TEXT PRIMARY KEY,
    section TEXT NOT NULL,
    domain TEXT NOT NULL,
    text TEXT NOT NULL,
    response_type TEXT NOT NULL,
    scale_min INTEGER NOT NULL,
    scale_max INTEGER NOT NULL,
    reverse_scored INTEGER NOT NULL,
    source TEXT NOT NULL,
    sort_order INTEGER NOT NULL
);
CREATE TABLE clients (
    id TEXT PRIMARY KEY,
    case_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    occupation TEXT NOT NULL,
    primary_issue TEXT NOT NULL,
    issue_category TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    next_session_at TEXT,
    intake_date TEXT NOT NULL,
    counseling_period TEXT NOT NULL,
    referral_source TEXT NOT NULL,
    family_composition TEXT NOT NULL,
    relationship_context TEXT NOT NULL,
    presenting_problem TEXT NOT NULL,
    counseling_goals TEXT NOT NULL,
    protective_factors TEXT NOT NULL,
    risk_notes TEXT NOT NULL,
    current_session_number INTEGER NOT NULL,
    total_sessions INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE counselor_client_assignments (
    client_id TEXT PRIMARY KEY REFERENCES clients(id) ON DELETE CASCADE,
    counselor_id TEXT NOT NULL,
    center_id TEXT NOT NULL,
    region_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE questionnaire_responses (
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL REFERENCES questionnaire_items(item_id),
    response_value INTEGER NOT NULL,
    PRIMARY KEY (client_id, item_id)
);
CREATE TABLE assessment_scores (
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    label TEXT NOT NULL,
    score REAL NOT NULL,
    max_score REAL NOT NULL,
    severity TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    PRIMARY KEY (client_id, code)
);
CREATE TABLE counseling_sessions (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    session_number INTEGER NOT NULL,
    date TEXT NOT NULL,
    modality TEXT NOT NULL,
    participants TEXT NOT NULL,
    goal TEXT NOT NULL,
    client_report TEXT NOT NULL,
    counselor_observation TEXT NOT NULL,
    interventions TEXT NOT NULL,
    client_response TEXT NOT NULL,
    change_since_last TEXT NOT NULL,
    homework TEXT NOT NULL,
    next_plan TEXT NOT NULL,
    UNIQUE(client_id, session_number)
);
CREATE INDEX idx_assignments_counselor ON counselor_client_assignments(counselor_id, status, client_id);
CREATE INDEX idx_clients_name ON clients(name);
CREATE INDEX idx_clients_issue ON clients(primary_issue);
CREATE INDEX idx_responses_client ON questionnaire_responses(client_id);
CREATE INDEX idx_sessions_client ON counseling_sessions(client_id, session_number);
"""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def build_database(target: Path, anchor: date) -> dict[str, int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".building.sqlite3")
    if temporary.exists():
        temporary.unlink()

    counselors = read_csv(DASHBOARD_DIR / "counselors.csv")
    cohort_rows = read_csv(DASHBOARD_DIR / "client_cohorts.csv")
    cohorts_by_counselor: dict[str, list[tuple[str, str]]] = {}
    for row in cohort_rows:
        slots = cohorts_by_counselor.setdefault(row["counselor_id"], [])
        slots.extend([(row["issue"], "standard")] * int(row["standard_count"]))
        slots.extend([(row["issue"], "monitor")] * int(row["monitor_count"]))
        slots.extend([(row["issue"], "priority")] * int(row["priority_review_count"]))

    conn = sqlite3.connect(temporary)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=OFF")
    conn.executescript(SCHEMA)
    questions = questionnaire_items()
    conn.executemany(
        "INSERT INTO questionnaire_items VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            (
                item["item_id"], item["section"], item["domain"], item["text"],
                item["response_type"], item["scale_min"], item["scale_max"],
                int(item["reverse_scored"]), item["source"], item["sort_order"],
            )
            for item in questions
        ],
    )

    authored = {case.id: case for case in CLIENT_CASES}
    authored_order = list(CLIENT_CASES)
    client_rows: list[tuple[Any, ...]] = []
    assignment_rows: list[tuple[Any, ...]] = []
    response_rows: list[tuple[Any, ...]] = []
    assessment_rows: list[tuple[Any, ...]] = []
    session_rows: list[tuple[Any, ...]] = []
    global_number = 0

    def flush() -> None:
        if not client_rows:
            return
        conn.executemany("INSERT INTO clients VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", client_rows)
        conn.executemany("INSERT INTO counselor_client_assignments VALUES (?,?,?,?,?,?)", assignment_rows)
        conn.executemany("INSERT INTO questionnaire_responses VALUES (?,?,?)", response_rows)
        conn.executemany("INSERT INTO assessment_scores VALUES (?,?,?,?,?,?,?,?)", assessment_rows)
        conn.executemany("INSERT INTO counseling_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", session_rows)
        client_rows.clear(); assignment_rows.clear(); response_rows.clear(); assessment_rows.clear(); session_rows.clear()

    for counselor in counselors:
        counselor_id = counselor["id"]
        slots = cohorts_by_counselor.get(counselor_id, [])
        expected = int(counselor["active_clients"])
        if len(slots) != expected:
            raise RuntimeError(f"{counselor_id}: cohort slots {len(slots)} != active_clients {expected}")
        rng = random.Random(DATASET_SEED + stable_seed(counselor_id))
        rng.shuffle(slots)
        for local_number, (issue, risk_tier) in enumerate(slots, start=1):
            global_number += 1
            authored_case = authored_order[local_number - 1] if counselor_id == PRIMARY_COUNSELOR_ID and local_number <= len(authored_order) else None
            if authored_case is not None:
                case_id = authored_case.id
                case_code = authored_case.case_code
            else:
                case_id = f"client-{global_number:05d}"
                case_code = f"FC-2026-{global_number:05d}"

            responses = generate_responses(case_id, issue, risk_tier)
            scores = calculate_assessments(responses)
            profile = build_profile(case_id, case_code, issue, risk_tier, anchor, authored_case)
            client_rows.append(profile["client"])
            assignment_rows.append((case_id, counselor_id, counselor["center_id"], counselor["region_id"], profile["intake_date"], "active"))
            response_rows.extend((case_id, item_id, value) for item_id, value in responses.items())
            assessment_rows.extend(
                (case_id, score["code"], score["label"], score["score"], score["max_score"], score["severity"], score["interpretation"], order)
                for order, score in enumerate(scores, start=1)
            )
            session_rows.extend(profile["sessions"])
            if len(client_rows) >= 200:
                flush()
    flush()

    metadata = {
        "dataset_kind": "fixed deterministic demonstration data",
        "contains_real_people": False,
        "seed": DATASET_SEED,
        "generated_at": datetime.combine(anchor, time(9, 0)).isoformat(),
        "counselor_count": len(counselors),
        "client_count": global_number,
        "question_count": len(questions),
        "response_count": global_number * len(questions),
    }
    conn.executemany("INSERT INTO dataset_metadata(key,value) VALUES (?,?)", [(key, json_text(value)) for key, value in metadata.items()])
    conn.commit()
    conn.execute("PRAGMA optimize")
    conn.execute("VACUUM")
    conn.close()
    temporary.replace(target)
    return {key: int(value) for key, value in metadata.items() if isinstance(value, int) and not isinstance(value, bool)}


def build_profile(case_id: str, case_code: str, issue: str, risk_tier: str, anchor: date, authored_case: Any | None) -> dict[str, Any]:
    rng = random.Random(DATASET_SEED + stable_seed(case_id))
    detail = ISSUE_DETAILS[issue]
    current_session = rng.randint(1, 4)
    next_date = anchor + timedelta(days=rng.randint(1, 18 if current_session == 1 else 13))
    first_session_date = next_date - timedelta(days=(current_session - 1) * 14)
    intake = (
        anchor - timedelta(days=rng.randint(1, 14))
        if current_session == 1
        else first_session_date - timedelta(days=rng.randint(2, 10))
    )

    if authored_case is not None:
        name = authored_case.name
        age = authored_case.age
        gender = authored_case.gender
        occupation = authored_case.occupation
        primary_issue = authored_case.primary_issue
        referral = authored_case.referral_source
        family = authored_case.family_composition
        relationship = authored_case.relationship_context
        problem = authored_case.presenting_problem
        goals = authored_case.counseling_goals
        protective = authored_case.protective_factors
        risks = authored_case.risk_notes
        intake = date.fromisoformat(authored_case.intake_date)
        current_session = authored_case.current_session_number
        next_session_at = datetime.combine(next_date, time(rng.choice([9, 10, 11, 13, 14, 15, 16]), rng.choice([0, 30]))).isoformat()
        sessions = [
            session_tuple(case_id, item, next_date + timedelta(days=(item.number - current_session) * 14))
            for item in authored_case.sessions
        ]
        total_sessions = len(sessions)
    else:
        gender = "여성" if rng.random() < 0.57 else "남성"
        given_names = FEMALE_GIVEN_NAMES if gender == "여성" else MALE_GIVEN_NAMES
        name = SURNAMES[rng.randrange(len(SURNAMES))] + given_names[rng.randrange(len(given_names))]
        age = rng.randint(27, 58)
        occupation = rng.choice(OCCUPATIONS)
        primary_issue = detail["primary"]
        referral = rng.choice(REFERRALS)
        partner_age = max(24, min(62, age + rng.randint(-4, 5)))
        child_count = rng.choice([0, 1, 1, 2, 2, 3])
        family = f"배우자({partner_age}세)" + (f", 자녀 {child_count}명과 동거" if child_count else "와 동거")
        relationship = detail["context"]
        problem = detail["problem"]
        goals = detail["goals"]
        protective = ["상담 참여 의지가 있음", "가족관계 개선 목표를 표현함", "갈등이 낮을 때 협력 경험이 있음"]
        risks = ["매 회기 안전 여부 직접 확인", "현재 확인된 즉각적 위기 징후 없음"] if risk_tier == "standard" else ["갈등 고조 시 안전 여부 재확인 필요", "첫 면담에서 원 응답과 현재 상황 대조 필요"]
        next_session_at = datetime.combine(next_date, time(rng.choice([9, 10, 11, 13, 14, 15, 16]), rng.choice([0, 30]))).isoformat()
        total_sessions = 4
        sessions = generated_sessions(case_id, name, issue, next_date, current_session, detail, total_sessions)

    completed = max(0, current_session - 1)
    status = "상담 시작 전" if completed == 0 else f"{completed}회기 완료 · {current_session}회기 준비"
    counseling_period = (
        f"{next_date.strftime('%Y.%m.%d')} 시작 예정"
        if current_session == 1
        else f"{intake.strftime('%Y.%m.%d')} ~ 진행 중"
    )
    client = (
        case_id, case_code, name, age, gender, occupation, primary_issue, issue, risk_tier,
        next_session_at, intake.isoformat(), counseling_period, referral, family, relationship,
        problem, json_text(goals), json_text(protective), json_text(risks), current_session,
        total_sessions, datetime.combine(intake, time(9, 0)).isoformat(), status,
    )
    return {"client": client, "sessions": sessions, "intake_date": intake.isoformat()}


def session_tuple(client_id: str, session: Any, session_date: date | None = None) -> tuple[Any, ...]:
    return (
        session.id, client_id, session.number, (session_date or date.fromisoformat(session.date)).isoformat(), session.modality,
        json_text(session.participants), session.goal, session.client_report,
        session.counselor_observation, json_text(session.interventions),
        session.client_response, session.change_since_last, session.homework, session.next_plan,
    )


def generated_sessions(client_id: str, name: str, issue: str, current_date: date, current_session: int, detail: dict[str, Any], total: int) -> list[tuple[Any, ...]]:
    changes = ["첫 회기", "갈등 장면을 한 차례 기록함", "감정과 요청을 구분해 표현함", "합의한 대화 방법을 일부 적용함"]
    responses = ["상담 목표와 기록 방식에 동의함", "반복되는 상호작용 순서를 이해했다고 표현함", "새로운 표현 방식을 연습함", "변화를 유지하기 위한 점검에 동의함"]
    observations = ["초반 긴장이 관찰되었으나 질문에 구체적으로 응답함", "갈등 장면을 설명할 때 말의 속도가 빨라짐", "감정 단어를 사용할 때 눈맞춤이 증가함", "이전보다 안정된 속도로 경험을 설명함"]
    sessions = []
    for number in range(1, total + 1):
        session_date = current_date + timedelta(days=(number - current_session) * 14)
        sessions.append((
            f"{client_id}-S{number:02d}", client_id, number, session_date.isoformat(), "대면",
            json_text([name] if issue not in {"부부갈등", "이혼 전후"} or number % 2 else [name, "배우자"]),
            detail["goals"][min(number - 1, len(detail["goals"]) - 1)],
            detail["problem"], observations[number - 1], json_text(detail["interventions"][: min(3, number + 1)]),
            responses[number - 1], changes[number - 1], "다음 회기 전 대화 장면과 감정을 한 차례 기록",
            detail["goals"][min(number, len(detail["goals"]) - 1)],
        ))
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--anchor-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    counts = build_database(args.output.resolve(), args.anchor_date)
    size_mb = args.output.resolve().stat().st_size / (1024 * 1024)
    print(json.dumps({"path": str(args.output.resolve()), "size_mb": round(size_mb, 1), **counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
