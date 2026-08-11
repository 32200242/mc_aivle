from __future__ import annotations

import hashlib
import random
from typing import Any


FRPS_CONFIRMATION_CUTOFF = 54


FRPS_ITEMS = [
    ("FRPS_01", "hostility", "서로 간에 불평, 불만이 많다"),
    ("FRPS_02", "avoidance", "갈등이 생기면 해결하려 하기보다 피해버린다"),
    ("FRPS_03", "hostility", "가족원 간에 욕설이나 큰소리를 내며 싸운다"),
    ("FRPS_04", "distance", "가족이 함께 사진 찍고 싶어 하지 않는다"),
    ("FRPS_05", "distance_avoidance", "집에 같이 있어도 서로 얼굴을 마주치고 싶어 하지 않는다"),
    ("FRPS_06", "distance", "함께 식사·여행·외출·쇼핑 등을 하고 싶어 하지 않는다"),
    ("FRPS_07", "communication", "가족 안에서 자신의 힘든 일을 말하는 것이 어렵다"),
    ("FRPS_08", "conflict_proneness", "가족원 간에 의견충돌이 쉽게 일어난다"),
    ("FRPS_09", "communication_breakdown", "가족 안에 대화다운 대화가 없다"),
    ("FRPS_10", "distance_intimacy", "포옹·손잡기 등의 친밀한 표현이 거의 없다"),
    ("FRPS_11", "affective_flatness", "가족 안에 웃음이 거의 없다"),
    ("FRPS_12", "home_comfort", "집에 있으면 마음이 편하지 않고 불편하다"),
    ("FRPS_13", "emotional_sharing_deficit", "서로의 고민과 상황에 관심이 없고 잘 알지 못한다"),
    ("FRPS_14", "distance_intimacy", "사랑한다는 표현을 직접적이든 간접적이든 하지 않는다"),
    ("FRPS_15", "hostility", "서로 짜증스럽게 말한다"),
    ("FRPS_16", "hostility_contempt", "서로 가시가 있는 말·비꼬는 말·공격적인 말을 한다"),
    ("FRPS_17", "control_coercion", "한 명이 일방적·강압적으로 자기 의사를 강요한다"),
    ("FRPS_18", "communication_breakdown_avoidance", "꼭 필요한 말이 아니면 서로 이야기하지 않는다"),
]

FSTRESS_ITEMS = [
    ("stress_transition", "지난 1년 사이에 내가 결혼을 했다"),
    ("stress_transition", "지난 1년 사이에 가족 중 누군가 결혼을 했다"),
    ("stress_fertility", "지난 1년 사이에 본인 또는 배우자가 임신·유산을 경험했다"),
    ("stress_fertility", "지난 1년 사이에 가족 중 누군가 임신·유산을 경험했다"),
    ("stress_transition", "지난 1년 사이에 본인 또는 배우자가 출산·입양을 했다"),
    ("stress_transition", "지난 1년 사이에 가족 중 누군가 출산·입양을 했다"),
    ("stress_relational", "지난 1년 사이에 본인 또는 배우자의 외도 문제가 있었다"),
    ("stress_relational", "지난 1년 사이에 가족 중 누군가 외도 문제를 겪었다"),
    ("stress_relational", "지난 1년 사이에 본인과 배우자가 별거 또는 이혼을 경험했다"),
    ("stress_relational", "지난 1년 사이에 가족 중 누군가 별거하거나 이혼했다"),
    ("stress_loss", "지난 1년 사이에 배우자가 사망했다"),
    ("stress_loss", "지난 1년 사이에 가족이나 가까운 친척 중 누군가 사망했다"),
    ("stress_parenting", "지난 1년 사이에 자녀를 위한 보육시설·학원을 새로 찾아야 했다"),
    ("stress_parenting_transition", "지난 1년 사이에 자녀가 입학했다"),
    ("stress_parenting", "지난 1년 사이에 자녀가 원하는 학교 입시에 실패했다"),
    ("stress_work_transition", "지난 1년 사이에 본인 또는 배우자가 은퇴했다"),
    ("stress_work_transition", "지난 1년 사이에 가족 중 누군가 은퇴했다"),
    ("stress_financial", "지난 1년 사이에 새로 대출을 받거나 빚을 졌다"),
    ("stress_financial", "지난 1년 사이에 가계지출이 급격히 늘었다"),
    ("stress_financial", "지난 1년 사이에 재산상의 손실을 보았다"),
    ("stress_work_transition", "지난 1년 사이에 사업을 시작하거나 첫 출근을 했다"),
    ("stress_work", "지난 1년 사이에 실직하거나 해고되었다"),
    ("stress_work", "지난 1년 사이에 직장을 얻는 데 실패했다"),
    ("stress_transition", "지난 1년 사이에 이사 또는 전학을 했다"),
    ("stress_inlaw_system", "지난 1년 사이에 가족 중 누군가 따로 살거나 함께 살게 되었다"),
    ("stress_health", "지난 1년 사이에 크게 다치거나 많이 아팠다"),
    ("stress_risk_behavior", "지난 1년 사이에 학교폭력이나 범죄 피해를 경험했다"),
    ("stress_risk_behavior", "지난 1년 사이에 가출·비행 또는 고소·고발 문제가 있었다"),
    ("stress_inlaw_expectation", "가족 중 누군가의 결혼 문제로 부담을 느끼고 있다"),
    ("stress_fertility", "본인 또는 배우자가 임신을 원했지만 되지 않았다"),
    ("stress_fertility", "가족 중 누군가 임신을 원했지만 되지 않았다"),
    ("stress_parenting_health", "자녀에게 발달상의 어려움이 있다"),
    ("stress_parenting", "자녀의 성적이 낮거나 이전보다 떨어졌다"),
    ("stress_health_care", "가족 중 누군가 요양병원에 있다"),
    ("stress_health_care", "가족이 돌봐야 할 고령 친척이 있다"),
    ("stress_inlaw_system", "부모님이나 가까운 친척들과 불화가 있다"),
    ("stress_relational", "부부의 친밀한 관계가 만족스럽지 않다"),
    ("stress_relational_risk", "가족 내 신체적·언어적 폭력 문제가 있다"),
    ("stress_financial", "가정경제에 만성적인 어려움이 있다"),
    ("stress_work", "사업 또는 직업상 어려움이 있다"),
    ("stress_financial_inlaw", "형편이 어려운 부모님이나 친척을 재정적으로 돕고 있다"),
    ("stress_health", "가족 중 누군가에게 만성질환이나 장애가 있다"),
    ("stress_mental_health", "본인 또는 가족에게 치료가 필요한 심리·정서 문제가 있다"),
    ("stress_addiction", "본인 또는 가족에게 음주 문제가 있다"),
    ("stress_addiction", "본인 또는 가족이 게임·인터넷·스마트폰 사용으로 일상에 어려움이 있다"),
]

BFI10_ITEMS = [
    ("BFI10_01", "extraversion", "나는 나 자신을 과묵한 사람이라고 본다", True),
    ("BFI10_02", "agreeableness", "나는 나 자신을 대체로 믿을 만한 사람이라고 본다", False),
    ("BFI10_03", "conscientiousness", "나는 나 자신을 일을 철저히 하는 사람이라고 본다", False),
    ("BFI10_04", "emotional_stability", "나는 나 자신을 느긋하며 스트레스를 잘 해소하는 사람이라고 본다", False),
    ("BFI10_05", "openness", "나는 나 자신을 상상력이 풍부한 사람이라고 본다", False),
    ("BFI10_06", "extraversion", "나는 나 자신을 외향적이고 사교적인 사람이라고 본다", False),
    ("BFI10_07", "agreeableness", "나는 나 자신을 다른 사람의 흠을 잘 잡는 사람이라고 본다", True),
    ("BFI10_08", "conscientiousness", "나는 나 자신을 게으른 경향이 있는 사람이라고 본다", True),
    ("BFI10_09", "emotional_stability", "나는 나 자신을 신경이 예민한 사람이라고 본다", True),
    ("BFI10_10", "openness", "나는 나 자신을 예술적 관심이 거의 없는 사람이라고 본다", True),
]


def questionnaire_items() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = 0
    for item_id, domain, text in FRPS_ITEMS:
        order += 1
        rows.append(_item(item_id, "FRPS", domain, text, "likert_1_5", 1, 5, False, "family_crisis_scale_2013", order))
    for index, (domain, text) in enumerate(FSTRESS_ITEMS, start=1):
        order += 1
        rows.append(_item(f"FSTRESS_{index:02d}", "FSTRESS", domain, text, "event_stress_0_5", 0, 5, False, "family_stress_scale_2013", order))
    for item_id, domain, text, reverse in BFI10_ITEMS:
        order += 1
        rows.append(_item(item_id, "BFI10", domain, text, "likert_1_5", 1, 5, reverse, "BFI10_Korean_GESIS", order))
    order += 1
    rows.append(_item("DIVORCE_01", "DIVORCE", "divorce_concern_level", "현재 이혼이나 별거를 실제 선택지로 고민하고 있습니까?", "ordinal_0_3", 0, 3, False, "intake_custom", order))
    return rows


def _item(item_id: str, section: str, domain: str, text: str, response_type: str, scale_min: int, scale_max: int, reverse_scored: bool, source: str, sort_order: int) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "section": section,
        "domain": domain,
        "text": text,
        "response_type": response_type,
        "scale_min": scale_min,
        "scale_max": scale_max,
        "reverse_scored": reverse_scored,
        "source": source,
        "sort_order": sort_order,
    }


def stable_seed(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big")


def generate_responses(case_id: str, issue: str, risk_tier: str) -> dict[str, int]:
    """Generate deterministic item responses without invoking an LLM."""

    rng = random.Random(stable_seed(case_id))
    risk_base = {"standard": 2.05, "monitor": 3.05, "priority": 4.05}.get(risk_tier, 2.4)
    stress_base = {"standard": 1.8, "monitor": 2.6, "priority": 3.35}.get(risk_tier, 2.2)
    event_probability = {"standard": 0.06, "monitor": 0.1, "priority": 0.15}.get(risk_tier, 0.08)
    if issue == "부부갈등":
        risk_base += 0.35
    elif issue == "이혼 전후":
        risk_base += 0.55
        stress_base += 0.25
    elif issue == "부모-자녀 갈등":
        stress_base += 0.35

    personality = {
        "extraversion": rng.gauss(3.0, 0.55),
        "agreeableness": rng.gauss(3.35 if risk_tier == "standard" else 2.8, 0.55),
        "conscientiousness": rng.gauss(3.25, 0.55),
        "emotional_stability": rng.gauss(3.3 if risk_tier == "standard" else 2.55, 0.6),
        "openness": rng.gauss(3.15, 0.55),
    }
    responses: dict[str, int] = {}
    for item in questionnaire_items():
        section = item["section"]
        domain = item["domain"]
        if section == "FRPS":
            domain_shift = 0.0
            if issue in {"부부갈등", "이혼 전후"} and any(token in domain for token in ("hostility", "communication", "distance")):
                domain_shift = 0.35
            value = _bounded_round(rng.gauss(risk_base + domain_shift, 0.72), 1, 5)
        elif section == "FSTRESS":
            domain_shift = 0.0
            probability_shift = 0.0
            if issue == "부모-자녀 갈등" and "parenting" in domain:
                domain_shift = 0.65
                probability_shift = 0.28
            if issue == "이혼 전후" and "relational" in domain:
                domain_shift = 0.7
                probability_shift = 0.38
            if issue == "부부갈등" and "relational" in domain:
                domain_shift = 0.45
                probability_shift = 0.2
            if issue == "기타 가족관계" and any(token in domain for token in ("inlaw", "health", "financial")):
                domain_shift = 0.35
                probability_shift = 0.18

            probability = event_probability + probability_shift
            if any(token in domain for token in ("risk_behavior", "addiction")):
                probability *= 0.4
            elif "mental_health" in domain:
                probability *= 0.65
            experienced = rng.random() < min(0.8, probability)
            value = _bounded_round(rng.gauss(stress_base + domain_shift, 0.8), 1, 5) if experienced else 0
        elif section == "BFI10":
            scored_target = _bounded_round(rng.gauss(personality[domain], 0.55), 1, 5)
            value = 6 - scored_target if item["reverse_scored"] else scored_target
        else:
            divorce_base = 0.25 if risk_tier == "standard" else 1.2 if risk_tier == "monitor" else 2.15
            if issue == "이혼 전후":
                divorce_base += 0.65
            value = _bounded_round(rng.gauss(divorce_base, 0.65), 0, 3)
        responses[item["item_id"]] = value
    return responses


def calculate_assessments(responses: dict[str, int]) -> list[dict[str, Any]]:
    items = {item["item_id"]: item for item in questionnaire_items()}
    frps_values = [responses[item_id] for item_id in responses if item_id.startswith("FRPS_")]
    stress_values = [responses[item_id] for item_id in responses if item_id.startswith("FSTRESS_")]
    personality_values: dict[str, list[int]] = {}
    for item_id, value in responses.items():
        if not item_id.startswith("BFI10_"):
            continue
        item = items[item_id]
        personality_values.setdefault(item["domain"], []).append(
            6 - value if item["reverse_scored"] else value
        )

    frps = sum(max(1, min(5, int(value))) for value in frps_values)
    stress_values = [max(0, min(5, int(value))) for value in stress_values]
    stress_experience_count = sum(value > 0 for value in stress_values)
    stress_total = sum(stress_values)
    divorce = float(responses.get("DIVORCE_01", 0))
    frps_severity = "확인 기준 이상" if frps >= FRPS_CONFIRMATION_CUTOFF else "확인 기준 미만"
    assessments = [
        _assessment(
            "FRPS", "가족관계 문제징후", frps, 90, frps_severity,
            f"18문항 원점수 합계이며 확인 기준은 {FRPS_CONFIRMATION_CUTOFF}점(문항 평균 3.0점) 이상임",
        ),
        _assessment(
            "FSTRESS", "가족스트레스", stress_total, 225, f"생활사건 {stress_experience_count}건 경험",
            f"지난 1년 또는 만성적으로 경험한 생활사건은 {stress_experience_count}/45건이며 경험 사건의 스트레스 합계는 {stress_total}/225점임",
        ),
    ]
    dimensions = [
        ("extraversion", "BFI10-E", "외향성"),
        ("agreeableness", "BFI10-A", "친화성"),
        ("conscientiousness", "BFI10-C", "성실성"),
        ("emotional_stability", "BFI10-ES", "정서적 안정성"),
        ("openness", "BFI10-O", "개방성"),
    ]
    for domain, code, label in dimensions:
        values = personality_values.get(domain, [])
        if values:
            assessments.append(
                _assessment(
                    code,
                    f"BFI-10 {label}",
                    round(sum(values) / len(values), 2),
                    5,
                    "참고용",
                    "두 문항으로 산출한 성격 차원 참고값이며 보호요인 점수나 개인 진단으로 해석하지 않음",
                )
            )
    assessments.append(
        _assessment(
            "DIVORCE", "관계 해체 고려", divorce, 3,
            response_label("ordinal_0_3", int(divorce)),
            "단일 접수문항의 현재 응답이며 위험등급·관계예후·실행 가능성을 뜻하지 않음",
        )
    )
    return assessments


def response_label(response_type: str, value: int, section: str = "") -> str:
    if response_type == "ordinal_0_3":
        return ["전혀 고려하지 않음", "생각해 본 적 있음", "구체적으로 고민 중", "현재 실제 선택지로 고려 중"][max(0, min(3, value))]
    if section == "FSTRESS":
        return [
            "경험 없음",
            "경험 있음 · 부담 매우 낮음",
            "경험 있음 · 부담 낮음",
            "경험 있음 · 부담 보통",
            "경험 있음 · 부담 높음",
            "경험 있음 · 부담 매우 높음",
        ][max(0, min(5, value))]
    return ["", "전혀 그렇지 않다", "그렇지 않은 편이다", "보통이다", "그런 편이다", "매우 그렇다"][max(1, min(5, value))]


def _bounded_round(value: float, lower: int, upper: int) -> int:
    return max(lower, min(upper, int(round(value))))


def _assessment(code: str, label: str, score: float, maximum: float, severity: str, interpretation: str) -> dict[str, Any]:
    return {
        "code": code,
        "label": label,
        "score": score,
        "max_score": maximum,
        "severity": severity,
        "interpretation": interpretation,
    }
