from __future__ import annotations

from typing import Any


PERSONAS: dict[str, dict[str, Any]] = {
    "lee-jieun": {
        "id": "lee-jieun",
        "name": "이지은 (가명)",
        "gender": "female",
        "gender_label": "여성",
        "age": 34,
        "occupation": "회계원",
        "marriage_period": "7년",
        "children": "1명 (5세)",
        "tts_speaker": "이지은 음성",
        "tts_voice_description": (
            "30대 중반 한국인 여성의 자연스러운 일상 대화 목소리. 맑지만 지나치게 높지 않은 음역, "
            "부드럽고 현실적인 호흡, 보통 속도. 성우·광고·뉴스 낭독처럼 또렷하게 연기하지 않고 "
            "가족상담실에서 바로 앞 사람에게 조용히 말하는 느낌"
        ),
    },
    "kim-minseok": {
        "id": "kim-minseok",
        "name": "김민석 (가명)",
        "gender": "male",
        "gender_label": "남성",
        "age": 42,
        "occupation": "영업관리직",
        "marriage_period": "7년",
        "children": "1명 (5세)",
        "tts_speaker": "김민석 음성",
        "tts_voice_description": (
            "40대 초반 한국인 남성의 자연스러운 일상 대화 목소리. 너무 굵거나 나이 들어 보이지 않는 "
            "편안한 중저음, 한국어 억양과 발음이 자연스럽고 보통 속도. 성우·광고·뉴스 낭독처럼 "
            "과장하지 않고 가족상담실에서 바로 앞 사람에게 조용히 말하는 느낌"
        ),
    },
}

DEFAULT_PERSONA_ID = "lee-jieun"


def get_persona(persona_id: str | None) -> dict[str, Any]:
    return PERSONAS.get(persona_id or DEFAULT_PERSONA_ID, PERSONAS[DEFAULT_PERSONA_ID])
