from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["central_admin", "center_admin", "counselor", "trainer"]
Emotion = Literal["neutral", "sad", "angry", "anxious", "hurt", "withdrawn"]


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


class TrainingSessionView(BaseModel):
    id: str
    scenario_id: str
    difficulty: str
    goal: str
    persona_name: str
    status: Literal["active", "completed"] = "active"


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


class AssessmentScore(BaseModel):
    code: str
    label: str
    score: float
    max_score: float
    severity: str
    interpretation: str


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
    sessions: list[CounselingSessionRecord]
    current_session_number: int


class DashboardSummary(BaseModel):
    center_count: int
    active_clients: int
    counseling_sessions: int
    ai_report_minutes: float
    satisfaction: float
    training_completion_rate: float


class CopilotRequest(BaseModel):
    transcript: str = Field(min_length=10, max_length=20000)
    session_goal: str = Field(default="의사소통 개선 및 관계 회복", max_length=500)
    counselor_note: str = Field(default="", max_length=5000)
    source_label: str = Field(default="상담 대화", max_length=120)
    source_type: Literal["manual", "synthetic_case", "case_record"] = "manual"
    client_id: str | None = None
    session_number: int | None = None


class CopilotCaseRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=80)
    session_number: int | None = Field(default=None, ge=1, le=1000)


class CopilotResult(BaseModel):
    provider: str
    model: str
    source_type: str = "manual"
    client_id: str | None = None
    session_number: int | None = None
    summary: str
    core_issues: list[str]
    observed_emotions: list[str]
    risk_signals: list[str]
    recommended_directions: list[str]
    suggested_questions: list[str]
    recommended_phrases: list[str]
    avoid_phrases: list[str]
    soap_draft: dict[str, str]


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


class OCRResult(BaseModel):
    provider: str
    raw_text: str
    clean_text: str
    pages: list[OCRPage]


class OCRStatus(BaseModel):
    provider: str
    available: bool
    detail: str
    gpu_available: bool = False


class OCRDocumentUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=120)
    data_base64: str = Field(min_length=4, max_length=20_000_000)


class OCRRequest(BaseModel):
    documents: list[OCRDocumentUpload] = Field(min_length=1, max_length=5)
    preprocess_mode: str = Field(default="문서 강화", max_length=40)
    form_hint: str = Field(default="자동 판별", max_length=80)
    use_gpu: bool = False


class RecordGenerateRequest(BaseModel):
    transcript: str = Field(default="", max_length=20000)
    session_goal: str = Field(default="의사소통 개선 및 관계 회복", max_length=500)
    counselor_note: str = Field(default="", max_length=8000)
    ocr_text: str = Field(default="", max_length=30000)
    manual_correction: str = Field(default="", max_length=10000)
    existing_summary: str = Field(default="", max_length=10000)
    form_hint: str = Field(default="자동 판별", max_length=80)


class IntegratedRecords(BaseModel):
    provider: str
    model: str
    initial_intake: dict[str, str]
    session_record: dict[str, str]
    soap: dict[str, str]
    uncertain_items: list[str]
    source_summary: dict[str, str]


class ReportGenerateRequest(BaseModel):
    records: IntegratedRecords
    case_summary: str = Field(default="", max_length=10000)
    session_change: str = Field(default="", max_length=5000)
    goal_status: str = Field(default="부분 달성", max_length=100)
    next_date: str = Field(default="미정", max_length=100)


class ReportResult(BaseModel):
    provider: str
    model: str
    session_report: str
    closing_report: str
    review_notice: str


class SpeechStatus(BaseModel):
    provider: str
    configured: bool
    detail: str


class SpeechTranscript(BaseModel):
    text: str
    provider: str
