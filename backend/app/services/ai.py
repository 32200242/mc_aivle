from __future__ import annotations

import asyncio
import ast
import json
import re
import uuid
from typing import Any

from ..config import settings
from ..schemas import NonverbalCue, TurnResult
from .behavior_catalog import CUE_INDEX, CUE_PROMPT, DEFAULT_CUES
from .llm import chat_completion


SCENARIOS = {
    "couple-conflict-01": {
        "situation": "결혼 7년차 부부. 5세 자녀가 있다. 생활비와 육아 분담 문제로 갈등이 반복된다.",
        "opening": "요즘 남편이랑 대화만 시작하면 결국 싸움으로 끝나요.",
        "need": "존중받는 느낌, 안전한 대화, 감정적으로 무시당하지 않는 경험",
    },
    "parenting-conflict-01": {
        "situation": "자녀의 학습과 훈육 방식을 두고 부부가 충돌하고 있다.",
        "opening": "아이 문제만 나오면 서로 누가 더 잘못했는지 따지게 돼요.",
        "need": "비난 대신 함께 문제를 해결한다는 경험",
    },
}

DIFFICULTY = {
    "beginner": "감정을 비교적 직접 표현하고 공감에 쉽게 반응한다.",
    "intermediate": "감정과 사실이 섞여 있고 방어와 호소가 함께 나타난다.",
    "advanced": "양가감정, 회피, 억울함이 섞여 있고 성급한 해석에 민감하다.",
}


def _clean_model_text(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<\|[^>]+\|>", "", cleaned)
    return cleaned.strip()


def _balanced_object_candidates(text: str):
    for start, char in enumerate(text):
        if char != "{":
            continue
        depth = 0
        quote: str | None = None
        escaped = False
        for end in range(start, len(text)):
            current = text[end]
            if quote:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    quote = None
                continue
            if current in {'"', "'"}:
                quote = current
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    yield text[start : end + 1]
                    break


def _parse_mapping(candidate: str) -> dict[str, Any] | None:
    variants = [
        candidate,
        re.sub(r",\s*([}\]])", r"\1", candidate),
        candidate.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})),
    ]
    for variant in variants:
        try:
            value = json.loads(variant)
            if isinstance(value, dict):
                return value
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            value = ast.literal_eval(variant)
            if isinstance(value, dict):
                return value
        except (ValueError, SyntaxError):
            pass
    return None


def extract_json_object(text: str) -> dict[str, Any] | None:
    candidate = _clean_model_text(text)
    if not candidate:
        return None
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", candidate, flags=re.DOTALL | re.IGNORECASE)
    sources = [*fenced, candidate]
    for source in sources:
        direct = _parse_mapping(source.strip())
        if direct is not None:
            return direct
        for fragment in _balanced_object_candidates(source):
            parsed = _parse_mapping(fragment)
            if parsed is None:
                continue
            for key in ("result", "output", "content", "text"):
                nested = parsed.get(key)
                if isinstance(nested, str):
                    nested_parsed = extract_json_object(nested)
                    if nested_parsed is not None:
                        return nested_parsed
            return parsed
    return None


def _mock_result(message: str) -> TurnResult:
    normalized = message.strip()
    if any(word in normalized for word in ("힘들", "불안", "걱정", "긴장")):
        response = "그 이야기를 꺼내는 것만으로도 마음이 좀 조여 오는 것 같아요. 상대가 제 말을 또 다르게 받아들일까 봐 먼저 긴장하게 돼요."
        emotion = "anxious"
        cue_ids = ["gaze.avoid_counselor", "hand.finger_wring"]
    elif any(word in normalized for word in ("화", "갈등", "싸움", "남편", "아내")):
        response = "처음에는 차분하게 말하려고 하는데, 제 말을 듣지 않는다는 느낌이 들면 금방 방어적으로 돼요. 그러고 나면 또 같은 방식으로 싸웠다는 생각에 지쳐요."
        emotion = "hurt"
        cue_ids = ["face.frown", "posture.arms_crossed"]
    else:
        response = "조금 더 생각해 보니 누가 옳은지 정하는 것보다 제 말을 끝까지 들어주는 경험이 필요한 것 같아요. 그 부분부터 이야기해 보고 싶어요."
        emotion = "neutral"
        cue_ids = ["posture.lean_forward"]
    cues = [
        NonverbalCue(id=cue_id, **CUE_INDEX[cue_id], intensity=0.72 - index * 0.06)
        for index, cue_id in enumerate(cue_ids)
    ]
    return TurnResult(
        turn_id=f"turn-{uuid.uuid4().hex[:12]}",
        response=response,
        emotion=emotion,
        emotion_intensity=0.72,
        nonverbal_cues=cues,
        tts_text=response,
        supervisor_feedback={
            "강점": ["개방형 질문으로 탐색을 이어갔습니다."],
            "보완점": ["내담자의 핵심 감정을 한 문장으로 반영해 보세요."],
            "권장질문": ["그 순간 가장 크게 느껴지는 감정은 무엇인가요?"],
            "주의할응답": ["상대방의 의도나 내담자의 감정을 단정하지 않습니다."],
        },
    )


def _training_messages(message: str, session: dict, history: list[dict]) -> list[dict[str, str]]:
    scenario = SCENARIOS.get(session.get("scenario_id"), SCENARIOS["couple-conflict-01"])
    history_text = "\n".join(
        f"상담사: {turn.get('counselor_message', '')}\n내담자: {turn.get('response', '')}"
        for turn in history[-6:]
    ) or "첫 턴"
    system = f"""
너는 가족센터 상담사 교육을 위한 가상 성인 내담자다. 실제 인물과 무관하다.
내담자로 자연스럽게 2~4문장으로 응답하고, 상담사의 공감 수준에 따라 조금씩 마음을 열거나 방어한다.
진단을 단정하지 말고 위기 단서가 있으면 두려움·압박감·무력감을 조심스럽게 표현한다.

[페르소나]
- 이름: 이지은(가명), 34세, 결혼 7년차, 5세 자녀 1명
- 상황: {scenario['situation']}
- 첫 호소: {scenario['opening']}
- 숨은 욕구: {scenario['need']}
- 난이도: {DIFFICULTY.get(session.get('difficulty'), DIFFICULTY['intermediate'])}
- 훈련 목표: {session.get('goal', '감정반영')}

반드시 유효한 JSON 객체 하나만 출력한다. 첫 문자는 {{, 마지막 문자는 }}여야 한다.
설명, 마크다운 코드펜스, 주석, 후행 쉼표를 절대 추가하지 않는다. 모든 키와 문자열은 큰따옴표를 사용한다.
emotion은 neutral, sad, angry, anxious, hurt, withdrawn 중 하나다.
nonverbal_cues는 아래 ID 중 현재 맥락에 맞는 1~3개만 선택하며 label/category는 출력하지 않는다.
supervisor_feedback의 각 목록은 1~2개로 제한한다.

출력 예시:
{{"response":"내담자 응답","emotion":"anxious","emotion_intensity":0.72,
"nonverbal_cues":[{{"id":"gaze.avoid_counselor","intensity":0.7,"delay_ms":0,"duration_ms":120000,"loop":true}}],
"supervisor_feedback":{{"강점":["..."],"보완점":["..."],"권장질문":["..."],"주의할응답":["..."]}},
"tts_text":"내담자 응답"}}

사용 가능한 비언어 행동:
{CUE_PROMPT}
""".strip()
    user = f"[이전 대화]\n{history_text}\n\n[상담사의 이번 발화]\n{message.strip()}\n\n위 지시의 JSON 객체만 출력하라."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _bounded(value: Any, default: float, minimum: float = 0, maximum: float = 1) -> float:
    try:
        return max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return default


def _first_value(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _normalize_result(data: dict[str, Any]) -> TurnResult:
    response = str(_first_value(data, "response", "client_response", "내담자 응답", "응답", default="")).strip()
    if not response:
        raise ValueError("믿:음 응답에 response가 없습니다.")
    emotion = str(_first_value(data, "emotion", "감정", default="neutral")).strip().lower()
    emotion = {
        "차분": "neutral", "중립": "neutral", "슬픔": "sad", "분노": "angry",
        "불안": "anxious", "상처": "hurt", "위축": "withdrawn", "회피": "withdrawn",
    }.get(emotion, emotion)
    if emotion not in DEFAULT_CUES:
        emotion = "neutral"
    raw_cues = _first_value(
        data, "nonverbal_cues", "nonverbal_behavior", "nonverbal_behaviors", "비언어 행동", default=[]
    )
    if isinstance(raw_cues, dict):
        raw_cues = raw_cues.get("cues") or [raw_cues]
    cues: list[NonverbalCue] = []
    seen: set[str] = set()
    for item in raw_cues if isinstance(raw_cues, list) else []:
        if isinstance(item, str):
            item = {"id": item}
        if not isinstance(item, dict):
            continue
        cue_id = str(item.get("id", ""))
        if cue_id not in CUE_INDEX:
            label = str(_first_value(item, "label", "행동", default=cue_id)).strip()
            cue_id = next((known_id for known_id, meta in CUE_INDEX.items() if meta["label"] == label), "")
        if cue_id not in CUE_INDEX or cue_id in seen:
            continue
        seen.add(cue_id)
        cues.append(NonverbalCue(
            id=cue_id,
            **CUE_INDEX[cue_id],
            intensity=_bounded(item.get("intensity"), 0.6, 0.15, 1),
            delay_ms=int(_bounded(item.get("delay_ms"), 0, 0, 15000)),
            duration_ms=int(_bounded(item.get("duration_ms"), 120000, 500, 120000)),
            loop=bool(item.get("loop", True)),
        ))
        if len(cues) == 3:
            break
    if not cues:
        cues = [NonverbalCue(id=cue_id, **CUE_INDEX[cue_id], intensity=0.58) for cue_id in DEFAULT_CUES[emotion]]
    feedback = _first_value(data, "supervisor_feedback", "슈퍼바이저 피드백", "피드백")
    if not isinstance(feedback, dict):
        feedback = {"보완점": ["슈퍼바이저 피드백 형식을 확인해 주세요."]}
    return TurnResult(
        turn_id=f"turn-{uuid.uuid4().hex[:12]}",
        response=response,
        emotion=emotion,
        emotion_intensity=_bounded(_first_value(data, "emotion_intensity", "감정 강도"), 0.65),
        nonverbal_cues=cues,
        supervisor_feedback=feedback,
        tts_text=str(_first_value(data, "tts_text", "TTS", default=response)).strip(),
    )


def _raw_response_text(raw: str) -> str:
    cleaned = _clean_model_text(raw)
    patterns = [
        r'["\'](?:response|client_response|내담자 응답|응답)["\']?\s*[:：]\s*["“\'](.*?)["”\']\s*(?:,|\})',
        r'(?:내담자 응답|응답)\s*[:：]\s*(.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.DOTALL | re.IGNORECASE)
        if match and match.group(1).strip():
            cleaned = match.group(1).strip()
            break
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:답변|내담자)\s*[:：]\s*", "", cleaned).strip()
    return cleaned[:1200]


def _result_from_unstructured(raw: str) -> TurnResult:
    response = _raw_response_text(raw)
    if not response:
        raise ValueError("믿:음이 빈 응답을 반환했습니다.")
    if any(word in response for word in ("불안", "긴장", "걱정", "두려")):
        emotion = "anxious"
    elif any(word in response for word in ("화가", "화나", "분노", "짜증")):
        emotion = "angry"
    elif any(word in response for word in ("상처", "서운", "무시")):
        emotion = "hurt"
    elif any(word in response for word in ("슬프", "눈물", "우울")):
        emotion = "sad"
    elif any(word in response for word in ("말하고 싶지", "모르겠", "그만", "피하고")):
        emotion = "withdrawn"
    else:
        emotion = "neutral"
    return _normalize_result({
        "response": response,
        "emotion": emotion,
        "emotion_intensity": 0.62,
        "nonverbal_cues": [{"id": cue_id, "intensity": 0.62} for cue_id in DEFAULT_CUES[emotion]],
        "supervisor_feedback": {
            "강점": ["상담사의 발화에 대한 내담자 반응을 이어갔습니다."],
            "보완점": ["구조화되지 않은 모델 응답이므로 비언어 행동은 정서 단서로 보완되었습니다."],
            "권장질문": ["그때 마음속에서 가장 크게 느껴진 것은 무엇인가요?"],
            "주의할응답": ["내담자의 감정이나 상대방의 의도를 단정하지 않습니다."],
        },
        "tts_text": response,
    })


async def generate_turn(message: str, session: dict, history: list[dict]) -> TurnResult:
    if settings.ai_provider == "mock":
        await asyncio.sleep(0.2)
        return _mock_result(message)
    raw = await chat_completion(_training_messages(message, session, history), max_tokens=950, temperature=0.25)
    data = extract_json_object(raw)
    if data:
        try:
            return _normalize_result(data)
        except ValueError:
            pass
    return _result_from_unstructured(raw)
