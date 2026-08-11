from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["central_admin", "counselor"]
Emotion = Literal["neutral", "sad", "angry", "anxious", "hurt", "withdrawn"]
PersonaGender = Literal["female", "male"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=2, max_length=120)


class UserView(BaseModel):
    id: str
    name: str
    role: Role
    center_id: str | None = None
    center_name: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class NonverbalCue(BaseModel):
    id: str
    label: str
    category: str
    intensity: float = Field(ge=0.0, le=1.0)
    delay_ms: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=120000, ge=500)
    loop: bool = True


class TrainingSessionCreate(BaseModel):
    scenario_id: str = "couple-conflict-01"
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    goal: str = "감정반영"
    persona_id: Literal["lee-jieun", "kim-minseok"] = "lee-jieun"


class TrainingSessionView(BaseModel):
    id: str
    scenario_id: str
    difficulty: str
    goal: str
    persona_name: str
    persona_id: str
    persona_gender: PersonaGender
    status: Literal["active", "ended", "completed"] = "active"


class TrainingCompleteRequest(BaseModel):
    elapsed_seconds: int = Field(default=0, ge=0, le=86_400)
    turn_count: int = Field(default=0, ge=0, le=1_000)


class TrainingUtteranceScores(BaseModel):
    empathy: int = Field(ge=0, le=100)
    open_question: int = Field(ge=0, le=100)
    nonjudgment: int = Field(ge=0, le=100)
    total: int = Field(ge=0, le=100)


class TrainingCompletionResult(BaseModel):
    session: TrainingSessionView
    completed: bool
    required_turns: int
    turn_count: int
    pre_scores: TrainingUtteranceScores | None = None
    post_scores: TrainingUtteranceScores | None = None
    score_change: int = 0


class TurnRequest(BaseModel):
    counselor_message: str = Field(min_length=1, max_length=3000)


class TurnResult(BaseModel):
    turn_id: str
    response: str
    emotion: Emotion
    emotion_intensity: float = Field(ge=0.0, le=1.0)
    nonverbal_cues: list[NonverbalCue]
    supervisor_feedback: dict[str, list[str] | str | int | float]
    tts_text: str


class ClientSummary(BaseModel):
    id: str
    case_code: str
    name: str
    age: int
    status: str
    session_count: int
    primary_issue: str
    next_session_at: str | None = None
    synthetic: bool = True


class ClientPage(BaseModel):
    items: list[ClientSummary]
    total: int
    page: int
    page_size: int
    pages: int


class AssessmentScore(BaseModel):
    code: str
    label: str
    score: float
    max_score: float
    severity: str
    interpretation: str


class QuestionnaireResponse(BaseModel):
    item_id: str
    section: str
    domain: str
    text: str
    response_type: str
    response_value: int
    response_label: str
    scale_min: int
    scale_max: int
    reverse_scored: bool = False


class OfficialSessionRecord(BaseModel):
    record_type: Literal["initial_intake", "session_record"]
    record_label: str
    fields: dict[str, str]
    soap: dict[str, str] = Field(default_factory=dict)
    finalized_at: str


class CounselingSessionRecord(BaseModel):
    id: str
    number: int
    date: str
    modality: str
    participants: list[str]
    goal: str
    client_report: str
    counselor_observation: str
    interventions: list[str]
    client_response: str
    change_since_last: str
    homework: str
    next_plan: str
    official_record: OfficialSessionRecord | None = None


class ClientCase(BaseModel):
    id: str
    case_code: str
    name: str
    age: int
    gender: str
    occupation: str
    status: str
    session_count: int
    primary_issue: str
    next_session_at: str | None = None
    synthetic: bool = True
    intake_date: str
    counseling_period: str
    referral_source: str
    family_composition: str
    relationship_context: str
    presenting_problem: str
    counseling_goals: list[str]
    protective_factors: list[str]
    risk_notes: list[str]
    assessments: list[AssessmentScore]
    questionnaire_responses: list[QuestionnaireResponse] = Field(default_factory=list)
    sessions: list[CounselingSessionRecord]
    current_session_number: int


class DashboardScope(BaseModel):
    type: Literal["national", "region", "center"]
    id: str | None = None
    label: str
    region_id: str | None = None
    center_id: str | None = None


class RegionDashboardMetric(BaseModel):
    id: str
    name: str
    short_name: str
    family_center_count: int
    healthy_center_count: int
    multicultural_center_count: int
    center_count: int
    population: int
    households: int
    annual_service_users_2022: int
    map_x: int
    map_y: int
    counselor_count: int
    active_clients: int
    sessions: int
    waitlist: int
    utilization_rate: float
    satisfaction: float
    selected: bool


class CenterDashboardMetric(BaseModel):
    id: str
    name: str
    region_id: str
    region_name: str
    center_type: str
    counselor_count: int
    active_clients: int
    sessions: int
    waitlist: int
    avg_wait_days: float
    utilization_rate: float
    satisfaction: float
    quality_score: float
    selected: bool


class CounselorDashboardMetric(BaseModel):
    id: str
    display_name: str
    center_id: str
    center_name: str
    region_id: str
    employment_type: str
    tenure_years: float
    weekly_capacity: int
    active_clients: int
    utilization_rate: float
    supervisor_eligible: bool
    training_completion_rate: float
    primary_specialty: str
    practice_completed_sessions: int = 0
    practice_score_change: float = 0.0


class IssueDashboardMetric(BaseModel):
    issue: str
    client_count: int
    standard_count: int
    monitor_count: int
    priority_review_count: int


class DailyDashboardMetric(BaseModel):
    date: str
    sessions: int
    new_intakes: int
    waitlist: int
    utilization_rate: float
    satisfaction: float


class ForecastPoint(BaseModel):
    date: str
    predicted_sessions: float
    lower: float
    upper: float


class ForecastLeaderboardRow(BaseModel):
    model: str
    mae: float
    mape: float


class ForecastModelSummary(BaseModel):
    selected_model: str
    validation_days: int
    cv_folds: int = 0
    mae: float
    mape: float
    engine: str = "fallback"
    ensemble_weights: dict[str, float] = Field(default_factory=dict)
    interval_method: str = ""
    leaderboard: list[ForecastLeaderboardRow]


class QueuePlanningSummary(BaseModel):
    method: str
    forecast_daily_demand: float
    daily_slot_capacity: float
    forecast_utilization_rate: float
    delay_probability: float
    current_waitlist: int
    steady_state_queue_sessions: float
    expected_queue_sessions: float
    expected_wait_days: float
    projected_backlog_after_horizon: float
    backlog_clearance_days: float | None
    planning_horizon_days: int
    recommended_additional_daily_slots: int
    pressure_level: str
    assumption: str


class ServiceTargetSummary(BaseModel):
    year: int
    family_counseling_users: int
    family_counseling_satisfaction: float
    scope_annual_contact_target: float
    scope_daily_contact_target: float
    scope_monthly_contact_target: float
    source: str
    interpretation: str


class PracticeDashboardSummary(BaseModel):
    participating_counselors: int = 0
    started_sessions: int = 0
    completed_sessions: int = 0
    completion_rate: float = 0.0
    average_turns: float = 0.0
    average_score_change: float = 0.0


class DashboardSummary(BaseModel):
    data_as_of: str
    period_start: str
    period_days: int
    scope: DashboardScope
    center_count: int
    counselor_count: int
    active_clients: int
    counseling_sessions: int
    waitlist_count: int
    avg_wait_days: float
    utilization_rate: float
    ai_report_minutes: float
    satisfaction: float
    pre_post_completion_rate: float
    training_completion_rate: float
    changes: dict[str, float]
    regions: list[RegionDashboardMetric]
    centers: list[CenterDashboardMetric]
    counselors: list[CounselorDashboardMetric]
    issues: list[IssueDashboardMetric]
    trend: list[DailyDashboardMetric]
    forecast: list[ForecastPoint]
    model: ForecastModelSummary
    queue: QueuePlanningSummary
    service_targets: ServiceTargetSummary
    practice: PracticeDashboardSummary = Field(default_factory=PracticeDashboardSummary)
    methodology: dict[str, str]


class CopilotRequest(BaseModel):
    transcript: str = Field(min_length=10, max_length=20000)
    session_goal: str = Field(default="의사소통 개선 및 관계 회복", max_length=500)
    counselor_note: str = Field(default="", max_length=5000)
    source_label: str = Field(default="상담 대화", max_length=120)
    source_type: Literal["manual", "synthetic_case", "case_record"] = "manual"
    client_id: str | None = None
    session_number: int | None = None
    assessment_evidence: list[str] = Field(default_factory=list, max_length=20)
    prior_session_evidence: list[str] = Field(default_factory=list, max_length=20)


class CopilotCaseRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=80)
    session_number: int | None = Field(default=None, ge=1, le=1000)


class CopilotModuleAnalysis(BaseModel):
    id: str
    title: str
    frameworks: list[str]
    evidence_level: Literal["사전문진 기반", "누적기록 기반", "확인 필요"]
    summary: str
    evidence: list[str]
    hypotheses: list[str]
    questions: list[str]
    limitation: str


class CopilotResult(BaseModel):
    provider: str
    model: str
    generation_mode: Literal["model", "fallback", "mock"] = "model"
    fallback_reason: str | None = None
    source_type: str = "manual"
    client_id: str | None = None
    session_number: int | None = None
    analysis_mode: Literal["pre_intake", "cumulative"] = "cumulative"
    source_scope: list[str] = Field(default_factory=list)
    summary: str
    core_issues: list[str]
    observed_emotions: list[str]
    risk_signals: list[str]
    recommended_directions: list[str]
    suggested_questions: list[str]
    recommended_phrases: list[str]
    avoid_phrases: list[str]
    soap_draft: dict[str, str]
    module_analyses: list[CopilotModuleAnalysis] = Field(default_factory=list)
    xai_notice: str = "AI 해석은 상담사의 검토를 위한 가설이며 진단이나 최종 판단이 아닙니다."


class AIStatus(BaseModel):
    provider: str
    model: str
    configured: bool
    reachable: bool | None = None
    detail: str = ""
    latency_ms: int | None = None


class OCRToken(BaseModel):
    page: str
    mode: str
    text: str
    confidence: float


class OCRPage(BaseModel):
    page: str
    detected_form: str
    raw_text: str
    clean_text: str
    tokens: list[OCRToken] = Field(default_factory=list)
    alternate_text: str | None = None
    review_reasons: list[str] = Field(default_factory=list)
    risk_terms: list[str] = Field(default_factory=list)
    omission_suspected: bool = False


class OCRResult(BaseModel):
    provider: str
    raw_text: str
    clean_text: str
    pages: list[OCRPage]
    warnings: list[str] = Field(default_factory=list)
    requires_review: bool = True
    risk_review_required: bool = False
    omission_suspected: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    benchmark_notice: str = "PaddleOCR-VL 1.6 내부 192개 표본 평가의 중요 문구 정확도는 96.43%로 자동 확정 기준 99%에 미달합니다."


class OCRStatus(BaseModel):
    provider: str
    available: bool
    detail: str
    gpu_available: bool = False
    model_id: str | None = None
    review_required: bool = True


class OCRDocumentUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=120)
    data_base64: str = Field(min_length=4, max_length=20_000_000)


class OCRRequest(BaseModel):
    documents: list[OCRDocumentUpload] = Field(min_length=1, max_length=5)
    preprocess_mode: str = Field(default="문서 강화", max_length=40)
    form_hint: str = Field(default="자동 판별", max_length=80)
    use_gpu: bool = True


class RecordGenerateRequest(BaseModel):
    record_type: Literal["initial_intake", "session_record"] = "session_record"
    include_soap: bool = False
    client_id: str | None = Field(default=None, max_length=80)
    session_number: int | None = Field(default=None, ge=1)
    transcript: str = Field(default="", max_length=20000)
    session_goal: str = Field(default="의사소통 개선 및 관계 회복", max_length=500)
    counselor_note: str = Field(default="", max_length=8000)
    ocr_text: str = Field(default="", max_length=30000)
    manual_correction: str = Field(default="", max_length=10000)
    ocr_reviewed: bool = False
    ocr_review_note: str = Field(default="", max_length=1000)
    ocr_review_flags: list[str] = Field(default_factory=list, max_length=30)
    existing_summary: str = Field(default="", max_length=10000)
    form_hint: str = Field(default="자동 판별", max_length=80)


class IntegratedRecords(BaseModel):
    provider: str
    model: str
    generation_mode: Literal["model", "fallback", "mock"] = "model"
    fallback_reason: str | None = None
    initial_intake: dict[str, str]
    session_record: dict[str, str]
    soap: dict[str, str]
    uncertain_items: list[str]
    source_summary: dict[str, str]


class SessionWorkflowItem(BaseModel):
    session_number: int
    status: Literal["locked", "ready", "completed"]
    required_record_type: Literal["initial_intake", "session_record"]
    required_record_label: str
    soap_attached: bool = False
    finalized_at: str | None = None
    service_date: str | None = None


class SessionWorkflow(BaseModel):
    client_id: str
    next_session_number: int | None
    total_sessions: int
    sessions: list[SessionWorkflowItem]


class FinalizeSessionRequest(BaseModel):
    records: IntegratedRecords
    include_soap: bool = False
    soap_source_label: str = Field(default="", max_length=255)
    service_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class ReportGenerateRequest(BaseModel):
    records: IntegratedRecords
    case_summary: str = Field(default="", max_length=10000)
    session_change: str = Field(default="", max_length=5000)
    goal_status: str = Field(default="부분 달성", max_length=100)
    next_date: str = Field(default="미정", max_length=100)


class ReportResult(BaseModel):
    provider: str
    model: str
    generation_mode: Literal["model", "fallback", "mock"] = "model"
    fallback_reason: str | None = None
    session_report: str
    closing_report: str
    review_notice: str


class SpeechStatus(BaseModel):
    provider: str
    configured: bool
    detail: str
    reachable: bool | None = None


class SpeechTranscript(BaseModel):
    text: str
    provider: str


class AvatarStatus(BaseModel):
    provider: str
    model: str | None = None
    configured: bool
    reachable: bool | None = None
    detail: str
    latency_ms: int | None = None
