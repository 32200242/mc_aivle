from __future__ import annotations


INITIAL_FIELDS = (
    "내담자 호소문제(주제)",
    "상담목표(내담자와 합의된 목표)",
    "상담계획",
    "상담내용",
    "가계도",
)

OFFICIAL_METADATA_FIELDS = (
    "사례번호",
    "상담자",
    "상담일자",
    "상담시작시각",
    "상담종료시각",
    "상담방법",
    "상담유형",
    "내담자1 성명",
    "내담자1 관계",
    "내담자1 성별",
    "내담자2 성명",
    "내담자2 관계",
    "내담자2 성별",
    "내담자3 성명",
    "내담자3 관계",
    "내담자3 성별",
    "내담자",
    "상담회기",
)

COUNSELING_METHODS = ("면접상담", "사이버상담", "방문상담", "전화상담")
COUNSELING_TYPES = ("이혼전후상담", "부부상담", "부모자녀상담", "그 외 가족상담", "개인상담")
OFFICIAL_RECORD_FIELD_MAX_LENGTH = 300

SESSION_FIELDS = (
    "접수 연계기관",
    "상담주제 1순위",
    "상담주제 2순위",
    "상담주제 3순위",
    "당회기 상담목표",
    "상담내용(상담개입)",
    "다음 회기 계획",
    "연계기관",
)

# The initial record is the baseline case record, so every narrative section in
# the official form must be completed before it can be finalized.  Ranked topics
# 2 and 3 and linked institutions remain optional on later session records.
REQUIRED_INITIAL_FIELDS = INITIAL_FIELDS
REQUIRED_SESSION_FIELDS = (
    "상담주제 1순위",
    "당회기 상담목표",
    "상담내용(상담개입)",
    "다음 회기 계획",
)
