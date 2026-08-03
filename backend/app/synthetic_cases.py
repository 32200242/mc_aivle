from __future__ import annotations

from .schemas import AssessmentScore, ClientCase, ClientSummary, CounselingSessionRecord


def _assessment(code: str, label: str, score: float, maximum: float, severity: str, interpretation: str) -> AssessmentScore:
    return AssessmentScore(
        code=code,
        label=label,
        score=score,
        max_score=maximum,
        severity=severity,
        interpretation=interpretation,
    )


def _session(
    case_code: str,
    number: int,
    date: str,
    participants: list[str],
    goal: str,
    client_report: str,
    counselor_observation: str,
    interventions: list[str],
    client_response: str,
    change_since_last: str,
    homework: str,
    next_plan: str,
    modality: str = "대면",
) -> CounselingSessionRecord:
    return CounselingSessionRecord(
        id=f"{case_code}-S{number:02d}",
        number=number,
        date=date,
        modality=modality,
        participants=participants,
        goal=goal,
        client_report=client_report,
        counselor_observation=counselor_observation,
        interventions=interventions,
        client_response=client_response,
        change_since_last=change_since_last,
        homework=homework,
        next_plan=next_plan,
    )


CLIENT_CASES = [
    ClientCase(
        id="client-001",
        case_code="FC-2026-001",
        name="김민지",
        age=32,
        gender="여성",
        occupation="사무직",
        status="4회기 진행 중",
        session_count=4,
        primary_issue="의사소통 단절 및 오해",
        next_session_at="2026-08-05T10:00:00+09:00",
        intake_date="2026-06-20",
        counseling_period="2026.06.20 ~ 진행 중",
        referral_source="가족센터 홈페이지 자가 신청",
        family_composition="배우자(35세, 기술직), 자녀 1명(5세)과 동거",
        relationship_context="결혼 7년 차. 맞벌이와 양육 분담 문제로 갈등이 누적되었으며 최근에는 필요한 말만 주고받는 시간이 늘어남.",
        presenting_problem="대화를 시작하면 배우자가 비난으로 받아들이고 방어적으로 반응한다고 느낀다. 내담자는 자신의 말이 존중받지 못한다는 서운함과 다시 다툴 것이라는 불안을 함께 보고함.",
        counseling_goals=["비난 없이 감정과 요청을 표현하기", "갈등 후 24시간 안에 복구 대화 시도하기", "주 1회 양육·가사 분담 점검하기"],
        protective_factors=["상담 참여 의지가 높음", "자녀 돌봄에 대한 공동 책임감", "갈등이 없을 때 협력 경험이 있음"],
        risk_notes=["자해·타해 및 신체폭력 보고 없음", "고성이 오간 경험은 있어 매 회기 안전 여부를 직접 확인"],
        assessments=[
            _assessment("FRPS", "가족관계 위기징후", 18, 45, "관심", "회피와 의사소통 단절 문항이 상대적으로 높음"),
            _assessment("FSTRESS", "가족 스트레스", 22, 30, "높음", "양육·가사 분담과 시간 부족 스트레스가 두드러짐"),
            _assessment("BFI10", "정서적 안정성", 6, 10, "보통", "긴장 상황에서 걱정이 증가하나 일상 기능은 유지됨"),
            _assessment("DIVORCE", "관계 해체 고려", 1, 3, "낮음", "일시적으로 별거를 생각했으나 구체적인 계획은 없다고 응답"),
        ],
        sessions=[
            _session("FC-SYN-2026-001", 1, "2026-06-20", ["김민지"], "호소문제와 반복 갈등 장면 파악", "배우자가 자신의 말을 듣기 전에 해결책이나 반박부터 제시해 대화를 포기하게 된다고 보고함.", "초반에 손을 무릎 위에 고정하고 시선을 자주 내렸으나 갈등 장면을 설명할 때 말의 속도가 빨라짐.", ["문제 외재화", "갈등 장면 순서화", "안전 및 폭력 여부 확인"], "누가 옳은지보다 반복되는 순서를 보는 설명에 동의했고, 대화를 피하는 자신의 반응도 순환의 일부일 수 있다고 표현함.", "첫 회기", "갈등 직전 생각·감정·행동을 한 번 기록", "배우자의 반응 전 내담자가 느끼는 취약 감정 탐색"),
            _session("FC-SYN-2026-001", 2, "2026-06-27", ["김민지", "배우자"], "비난-방어 순환을 공동 문제로 명명", "주말 양육 분담을 이야기하다 서로 '항상'과 '절대'라는 표현을 사용하며 언성이 높아졌다고 보고함.", "두 사람 모두 상대 발언 중 끼어들었으나 순환 도식화 후 말의 속도가 낮아짐. 내담자는 배우자 발언 중 입술을 다무는 모습이 반복됨.", ["순환 도식화", "정서 반영", "말 끊지 않고 2분 듣기"], "두 사람이 문제를 상대의 성격이 아니라 반복 패턴으로 부르는 데 동의함.", "갈등 장면을 기록했으나 감정 단어는 주로 '화남'으로 표현함.", "하루 한 번 사실-감정-요청 문장 연습", "분노 아래의 서운함과 두려움을 구체화"),
            _session("FC-SYN-2026-001", 3, "2026-07-11", ["김민지"], "취약 감정과 관계 욕구 표현 연습", "배우자가 휴대폰을 보며 대답했을 때 무시당했다는 느낌과 혼자 양육하는 것 같은 막막함이 들었다고 보고함.", "이전보다 눈맞춤이 늘었고 서운함을 말할 때 눈물이 고였으나 호흡을 조절하며 설명을 이어감.", ["감정 명료화", "I-메시지 리허설", "예외 상황 탐색"], "'당신은 관심이 없어' 대신 '대답이 없으면 혼자라고 느껴져'라고 말하는 연습을 수행함.", "배우자와 10분 대화를 한 차례 시도했고 큰 다툼 없이 종료함.", "주 2회 10분 체크인", "복구 대화에서 구체적 요청과 경계 표현 점검"),
            _session("FC-SYN-2026-001", 4, "2026-07-25", ["김민지", "배우자"], "복구 대화와 역할 협상 강화", "양육 일정 변경을 두고 긴장했지만 잠시 멈춘 뒤 필요한 도움을 구체적으로 요청했다고 보고함.", "초반 긴장된 미소가 있었으나 두 사람의 발언 교대가 이전보다 안정적이었고 고개 끄덕임이 관찰됨.", ["긍정 상호작용 강화", "역할 협상", "타임아웃 및 재개 시점 합의"], "토요일 오전 돌봄과 평일 저녁 가사 항목을 구체적으로 재조정함.", "갈등 강도는 8점에서 5점으로 감소했다고 보고함.", "합의한 분담표를 2주 시험", "합의 유지 여부와 정서적 친밀감 회복 행동 확인"),
        ],
        current_session_number=4,
    ),
    ClientCase(
        id="client-002",
        case_code="FC-2026-002",
        name="이수현",
        age=41,
        gender="여성",
        occupation="자영업",
        status="3회기 진행 중",
        session_count=3,
        primary_issue="부부 역할 및 가치관 차이",
        next_session_at="2026-08-05T11:30:00+09:00",
        intake_date="2026-07-02",
        counseling_period="2026.07.02 ~ 진행 중",
        referral_source="지역 가족센터 전화 접수",
        family_composition="배우자(43세, 회사원), 자녀 2명(중학생·초등학생)과 동거",
        relationship_context="결혼 16년 차. 자영업 운영과 자녀 돌봄을 병행하면서 부부의 경제 기여와 가사 책임에 대한 평가가 엇갈림.",
        presenting_problem="배우자가 경제활동을 우선하면서 가정 의사결정은 일방적으로 한다고 느낀다. 배우자는 자신이 책임을 많이 지고 있는데 인정받지 못한다고 반응함.",
        counseling_goals=["역할 기대를 구체적인 행동 단위로 합의하기", "가치관 차이를 인신공격 없이 말하기", "부부 공동 의사결정 절차 만들기"],
        protective_factors=["자녀 관련 의사결정에서는 협력 경험이 있음", "경제 정보를 공유할 의사가 있음", "두 사람 모두 관계 유지 의사 표현"],
        risk_notes=["신체적 위협 보고 없음", "경제 통제 여부는 구체 사례를 통해 추가 확인 필요"],
        assessments=[
            _assessment("FRPS", "가족관계 위기징후", 21, 45, "관심", "강압·비꼼 및 대화 회피 영역 확인 필요"),
            _assessment("FSTRESS", "가족 스트레스", 24, 30, "높음", "경제·일-가정 양립 스트레스가 높음"),
            _assessment("BFI10", "개방성", 7, 10, "보통 이상", "대안 탐색에는 개방적이나 핵심 가치 충돌 시 입장이 경직됨"),
            _assessment("DIVORCE", "관계 해체 고려", 2, 3, "중간", "최근 6개월 내 별거를 언급한 적이 있어 의도와 계획을 직접 확인"),
        ],
        sessions=[
            _session("FC-SYN-2026-002", 1, "2026-07-02", ["이수현"], "역할 갈등과 안전·통제 이슈 사정", "수입이 일정하지 않다는 이유로 자신의 의견이 가볍게 취급된다고 보고함.", "목소리는 차분했으나 경제 문제를 말할 때 팔짱을 끼고 표정이 굳어짐.", ["역할 기대 탐색", "경제적 의사결정 과정 확인", "위기 선별"], "역할 문제를 기여도의 우열이 아니라 합의되지 않은 기대의 충돌로 정리하는 데 동의함.", "첫 회기", "각자가 담당한다고 생각하는 역할 목록 작성", "배우자 동반 회기에서 기대 차이를 비교"),
            _session("FC-SYN-2026-002", 2, "2026-07-09", ["이수현", "배우자"], "역할 기대 불일치 가시화", "배우자는 생계 책임, 내담자는 가정 운영과 정서적 돌봄의 부담을 각각 강조함.", "서로의 목록을 들을 때 한숨과 말 끊기가 있었으나 재진술 과제에는 참여함.", ["역할 카드 분류", "상대 관점 재진술", "공통 목표 확인"], "자녀 일정 관리가 보이지 않는 노동이었다는 점을 배우자가 일부 인정함.", "역할 목록을 작성해 왔으나 중요도 평가는 달랐음.", "일주일간 가사·돌봄 시간 기록", "시간 자료를 바탕으로 현실적인 재배분 협상"),
            _session("FC-SYN-2026-002", 3, "2026-07-23", ["이수현", "배우자"], "공동 의사결정 규칙 합의", "예상 밖 지출을 두고 다툼이 있었지만 계좌 내역을 함께 확인한 뒤 대화를 재개했다고 보고함.", "초반 시선 회피가 있었으나 숫자와 일정표를 함께 볼 때 협력적 태도가 증가함.", ["의사결정 프로토콜", "구체적 요청", "합의 검토"], "일정 금액 이상 지출은 사전 공유하고 주 1회 20분 운영회의를 하기로 합의함.", "가사 기록을 통해 체감 부담의 차이를 확인함.", "2주간 운영회의 실시", "합의 이행과 경제 통제 우려 재평가"),
        ],
        current_session_number=3,
    ),
    ClientCase(
        id="client-003",
        case_code="FC-2026-003",
        name="한지은",
        age=35,
        gender="여성",
        occupation="보건직",
        status="2회기 진행 중",
        session_count=2,
        primary_issue="양육 방식 충돌과 자녀 위축 우려",
        next_session_at="2026-08-06T14:00:00+09:00",
        intake_date="2026-07-18",
        counseling_period="2026.07.18 ~ 진행 중",
        referral_source="학교 상담교사 정보 제공 후 자가 신청",
        family_composition="배우자(37세, 공무원), 자녀 1명(초등학교 2학년)과 동거",
        relationship_context="자녀의 학습 습관과 규칙 위반에 대한 대응이 다르다. 내담자는 설명과 기다림을, 배우자는 즉각적이고 일관된 제재를 선호함.",
        presenting_problem="양육 문제만 나오면 배우자가 자신을 무책임한 부모로 평가한다고 느끼며, 자녀가 부모의 다툼을 눈치 보고 위축되는 것을 걱정함.",
        counseling_goals=["자녀 앞에서 양육 논쟁 중단하기", "부부 공통 규칙 3개 합의하기", "자녀 행동과 부모 감정을 구분하여 반응하기"],
        protective_factors=["자녀의 안정이라는 공통 목표", "가족 활동을 정기적으로 유지", "양육 정보를 함께 찾아본 경험"],
        risk_notes=["자녀 신체 체벌 보고 없음", "자녀 앞 고성 빈도와 정서적 영향 지속 확인"],
        assessments=[
            _assessment("FRPS", "가족관계 위기징후", 15, 45, "보통", "갈등 빈도보다 양육 주제의 집중도가 높음"),
            _assessment("FSTRESS", "가족 스트레스", 20, 30, "높음", "양육 및 교대근무 피로가 주요 요인"),
            _assessment("BFI10", "친화성", 8, 10, "높음", "갈등 회피로 요구 표현이 늦어질 수 있음"),
            _assessment("DIVORCE", "관계 해체 고려", 0, 3, "낮음", "관계 해체 생각은 없다고 응답"),
        ],
        sessions=[
            _session("FC-SYN-2026-003", 1, "2026-07-18", ["한지은"], "양육 갈등 장면과 자녀 영향 파악", "숙제 미완료 상황에서 부부가 서로의 양육 태도를 비난했고 자녀가 방으로 들어갔다고 보고함.", "자녀 반응을 설명할 때 눈물이 고였고 자신의 의견을 말할 때 문장 끝을 흐리는 모습이 관찰됨.", ["양육 갈등 장면 분석", "자녀 노출 최소화 계획", "부모 공동 목표 확인"], "자녀 앞 논쟁을 멈추고 나중에 이야기하는 신호가 필요하다고 동의함.", "첫 회기", "양육 갈등 발생 시간·상황 기록", "배우자와 공통 규칙 및 중단 신호 합의"),
            _session("FC-SYN-2026-003", 2, "2026-07-29", ["한지은", "배우자"], "공통 양육 원칙과 중단 신호 만들기", "숙제와 취침 문제를 둘러싼 기준이 서로 달랐음을 확인함.", "배우자는 초반 빠른 말투를 보였으나 자녀가 다툼을 피한다는 설명 후 침묵하며 들음.", ["공통 양육 가치 탐색", "규칙 구체화", "부부 논쟁 중단 신호 리허설"], "취침·화면시간·숙제 확인의 세 규칙을 2주간 동일하게 적용하기로 함.", "논쟁을 한 차례 다른 방에서 이어가 자녀 노출을 줄임.", "세 규칙 실행표 작성", "자녀 반응과 부모의 일관성 점검"),
        ],
        current_session_number=2,
    ),
    ClientCase(
        id="client-004",
        case_code="FC-2026-004",
        name="오지아",
        age=38,
        gender="여성",
        occupation="프리랜서",
        status="초기 상담",
        session_count=1,
        primary_issue="가족 돌봄 부담과 정서적 소진",
        next_session_at="2026-08-08T15:00:00+09:00",
        intake_date="2026-07-30",
        counseling_period="2026.07.30 ~ 진행 중",
        referral_source="지역 복지관 연계",
        family_composition="배우자(40세), 자녀 2명과 동거. 인근에 거주하는 모친의 병원 동행을 주로 담당",
        relationship_context="자녀 돌봄과 원가족 돌봄을 함께 맡으며 휴식 시간이 부족하다. 배우자는 경제활동 부담을 이유로 돌봄 분담 논의를 피하는 경향이 있음.",
        presenting_problem="가족이 자신을 필요로 하지만 정작 자신의 어려움은 아무도 묻지 않는다고 느낀다. 최근 짜증과 무기력, 수면 부족이 증가했다고 보고함.",
        counseling_goals=["돌봄 부담을 가시화하고 지원 요청하기", "주 2회 최소 휴식 시간 확보", "소진과 우울 위험을 지속 확인하기"],
        protective_factors=["복지관과 연결되어 있음", "친구 1명에게 도움을 요청할 수 있음", "상담 및 가족회의 의사 있음"],
        risk_notes=["자해 사고는 부인함", "수면·식사·일상 기능 저하가 지속되면 정신건강 전문 평가 연계 검토"],
        assessments=[
            _assessment("FRPS", "가족관계 위기징후", 17, 45, "관심", "정서적 공유 부족과 역할 불균형 확인 필요"),
            _assessment("FSTRESS", "가족 스트레스", 27, 30, "매우 높음", "돌봄·건강·경제 스트레스가 중첩됨"),
            _assessment("BFI10", "정서적 안정성", 4, 10, "낮음", "현재 스트레스 상황의 영향 가능성이 있어 상태 요인과 구분 필요"),
            _assessment("DIVORCE", "관계 해체 고려", 1, 3, "낮음", "관계를 끝내기보다 혼자 쉬고 싶다는 표현으로 확인됨"),
        ],
        sessions=[
            _session("FC-SYN-2026-004", 1, "2026-07-30", ["오지아"], "돌봄 부담·기능 저하·위기 여부 초기 사정", "최근 한 달간 평균 수면이 5시간 미만이고 사소한 일에도 화가 난 뒤 죄책감을 느낀다고 보고함.", "몸을 앞으로 숙이고 한숨을 자주 쉬었으며 도움을 요청하는 이야기에 긴 침묵이 나타남.", ["부담 영역 지도화", "위기 및 기능 사정", "즉시 활용 가능한 지원자 탐색"], "자신의 피로를 개인적 무능이 아니라 누적된 돌봄 부담으로 보는 관점에 안도감을 표현함.", "첫 회기", "일주일 돌봄 시간표와 도움 요청 가능한 항목 표시", "배우자 또는 가족 참여 가능성 확인 및 지역 돌봄 자원 검토"),
        ],
        current_session_number=1,
    ),
]


def get_client_case(client_id: str) -> ClientCase | None:
    return next((item for item in CLIENT_CASES if item.id == client_id), None)


def get_session(case: ClientCase, session_number: int | None = None) -> CounselingSessionRecord:
    selected_number = session_number or case.current_session_number
    return next((item for item in case.sessions if item.number == selected_number), case.sessions[-1])


def client_summaries() -> list[ClientSummary]:
    return [
        ClientSummary(
            id=case.id,
            case_code=case.case_code,
            name=case.name,
            age=case.age,
            status=case.status,
            session_count=case.session_count,
            primary_issue=case.primary_issue,
            next_session_at=case.next_session_at,
            synthetic=case.synthetic,
        )
        for case in CLIENT_CASES
    ]


def build_case_analysis_context(case: ClientCase, session: CounselingSessionRecord) -> str:
    assessments = "\n".join(
        f"- {item.code} {item.label}: {item.score:g}/{item.max_score:g}, {item.severity}; {item.interpretation}"
        for item in case.assessments
    )
    completed_sessions = [item for item in case.sessions if item.number < session.number]
    prior_sessions = "\n".join(
        f"- {item.number}회기({item.date}): 목표={item.goal}; 내담자 보고={item.client_report}; "
        f"관찰={item.counselor_observation}; 반응={item.client_response}; 변화={item.change_since_last}"
        for item in completed_sessions
    ) or "- 완료된 이전 회기 없음. 1회기 준비 분석은 사전문진과 접수정보만 사용함."
    return f"""[자료 성격]
실제 인물과 무관한 합성 사례 데이터. 실제 상담기록과 유사한 구조로 만든 시연 자료임.

[사례 식별]
사례번호: {case.case_code}
내담자: {case.name}(가상), {case.age}세, {case.gender}, {case.occupation}
접수일: {case.intake_date}
의뢰 경로: {case.referral_source}
가족 구성: {case.family_composition}

[관계·호소 맥락]
{case.relationship_context}
주호소: {case.presenting_problem}

[합의된 상담 목표]
{chr(10).join(f'- {goal}' for goal in case.counseling_goals)}

[보호요인]
{chr(10).join(f'- {item}' for item in case.protective_factors)}

[위기·확인 기록]
{chr(10).join(f'- {item}' for item in case.risk_notes)}

[사전 문진]
{assessments}

[완료된 이전 회기 기록: {len(completed_sessions)}건]
{prior_sessions}

[분석 기준]
{session.number}회기 시작 전 상담 준비 분석
예정 회기 목표: {session.goal}
자료 원칙: 선택한 {session.number}회기 자체의 사후 기록은 사용하지 않고 {session.number - 1}회기까지 완료된 기록만 사용함.
""".strip()
