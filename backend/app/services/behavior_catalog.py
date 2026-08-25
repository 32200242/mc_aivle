from __future__ import annotations


CLIENT_CUES = [
    ("posture.lean_forward", "자세·몸의 방향", "몸을 앞으로 기울여 앉음"),
    ("posture.recline", "자세·몸의 방향", "의자 등받이에 기대 뒤로 젖혀 앉음"),
    ("posture.arms_crossed", "자세·몸의 방향", "팔짱 끼기"),
    ("posture.legs_crossed", "자세·몸의 방향", "다리 꼬기"),
    ("posture.foot_tap", "자세·몸의 방향", "다리를 떨거나 발끝을 반복적으로 움직임"),
    ("posture.hunch", "자세·몸의 방향", "몸을 웅크리거나 어깨를 오므림"),
    ("posture.turn_away", "자세·몸의 방향", "몸을 문 쪽/상담사 반대 방향으로 돌림"),
    ("posture.frequent_shift", "자세·몸의 방향", "자주 자세를 바꾸거나 의자 위치를 옮김"),
    ("gaze.avoid_counselor", "시선·눈 맞춤", "상담사와 눈을 잘 마주치지 못함"),
    ("gaze.floor_or_wall", "시선·눈 맞춤", "바닥이나 옆 벽을 자주 응시함"),
    ("gaze.topic_avoid", "시선·눈 맞춤", "특정 주제에서만 시선을 갑자기 피함"),
    ("gaze.intense", "시선·눈 맞춤", "상담사를 강하게, 오래 쳐다봄"),
    ("gaze.fixed_side", "시선·눈 맞춤", "한쪽만 반복적으로 바라봄"),
    ("gaze.frequent_blink_teary", "시선·눈 맞춤", "눈을 자주 깜박이거나 눈물이 고이는 모습"),
    ("face.flat", "얼굴 표정", "미소를 거의 보이지 않음"),
    ("face.tense_smile", "얼굴 표정", "어색하거나 긴장된 미소"),
    ("face.frown", "얼굴 표정", "눈썹을 찡그리거나 이마에 주름을 자주 만듦"),
    ("face.lip_press_bite", "얼굴 표정", "입술을 꽉 다물거나 깨무는 모습"),
    ("face.collapse_with_sigh", "얼굴 표정", "한숨과 함께 표정이 급격히 무너짐"),
    ("face.flush_pale", "얼굴 표정", "특정 주제에서 얼굴이 붉어지거나 창백해짐"),
    ("hand.finger_wring", "손·팔·제스처", "손가락을 꼬거나 비비는 행동"),
    ("hand.touch_hair_face", "손·팔·제스처", "손으로 머리카락/얼굴을 반복적으로 만짐"),
    ("hand.pick_nails", "손·팔·제스처", "손톱이나 손가락을 뜯음"),
    ("hand.fidget_object", "손·팔·제스처", "펜, 종이, 물건을 계속 만지작거림"),
    ("hand.fist_table_tap", "손·팔·제스처", "주먹을 쥐거나 테이블을 두드림"),
    ("hand.large_gesture", "손·팔·제스처", "손을 크게 쓰며 과장된 제스처로 말함"),
    ("hand.fixed_on_lap", "손·팔·제스처", "손을 무릎 위에 고정하고 거의 움직이지 않음"),
    ("voice.fast", "말의 속도·톤·호흡", "평소보다 빠른 말 속도"),
    ("voice.slow_long_pause", "말의 속도·톤·호흡", "말이 느려지거나 문장 사이 침묵이 길어짐"),
    ("voice.tremble", "말의 속도·톤·호흡", "목소리가 떨리는 모습"),
    ("voice.volume_shift", "말의 속도·톤·호흡", "음량이 갑자기 커지거나 작아짐"),
    ("voice.deep_sigh", "말의 속도·톤·호흡", "말 도중 깊은 한숨을 자주 쉼"),
    ("voice.shallow_rapid_breath", "말의 속도·톤·호흡", "얕고 빠른 호흡"),
    ("voice.topic_breath_hold", "말의 속도·톤·호흡", "특정 주제를 말할 때 호흡이 멈추는 듯한 정지"),
    ("space.increase_distance", "거리·공간 사용", "상담사와의 물리적 거리를 늘리려 뒤로 물러남"),
    ("space.close_to_table", "거리·공간 사용", "테이블에 바짝 다가와 앉음"),
    ("space.shield_with_object", "거리·공간 사용", "가방·코트·물건을 몸 앞에 두고 방패처럼 사용함"),
    ("space.near_door_check", "거리·공간 사용", "문 가까이에 앉거나 문 방향을 자주 확인함"),
    ("space.scan_room", "거리·공간 사용", "방 안을 둘러보며 주변을 자주 살핌"),
    ("behavior.clock_check", "행동·움직임 패턴", "회기 중 시계를 자주 확인함"),
    ("behavior.phone_focus", "행동·움직임 패턴", "휴대폰을 자주 만지거나 알림에 집중함"),
    ("behavior.topic_turn_shift", "행동·움직임 패턴", "특정 주제에서 갑자기 몸을 돌리거나 자세를 바꿈"),
    ("behavior.joke_avoid", "행동·움직임 패턴", "웃음·농담을 과도하게 사용해 주제를 회피함"),
    ("behavior.stand_request", "행동·움직임 패턴", "앉았다 일어나거나 화장실·물 등을 자주 요청함"),
]

CUE_INDEX = {cue_id: {"category": category, "label": label} for cue_id, category, label in CLIENT_CUES}
CUE_PROMPT = "\n".join(f"- {cue_id}: {label}" for cue_id, _, label in CLIENT_CUES)

DEFAULT_CUES = {
    "neutral": ["hand.fixed_on_lap"],
    "sad": ["posture.hunch", "gaze.floor_or_wall"],
    "angry": ["face.frown", "gaze.intense"],
    "anxious": ["gaze.avoid_counselor", "hand.finger_wring"],
    "hurt": ["face.lip_press_bite", "gaze.topic_avoid"],
    "withdrawn": ["posture.recline", "posture.arms_crossed"],
}

