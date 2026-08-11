export type Role = "central_admin" | "counselor";

export type User = {
  id: string;
  name: string;
  role: Role;
  center_id?: string | null;
  center_name?: string | null;
};

export type ClientSummary = {
  id: string;
  case_code: string;
  name: string;
  age: number;
  status: string;
  session_count: number;
  primary_issue: string;
  next_session_at?: string | null;
  synthetic: boolean;
};

export type ClientPage = {
  items: ClientSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type AssessmentScore = {
  code: string;
  label: string;
  score: number;
  max_score: number;
  severity: string;
  interpretation: string;
};

export type QuestionnaireResponse = {
  item_id: string;
  section: "FRPS" | "FSTRESS" | "BFI10" | "DIVORCE" | string;
  domain: string;
  text: string;
  response_type: string;
  response_value: number;
  response_label: string;
  scale_min: number;
  scale_max: number;
  reverse_scored: boolean;
};

export type CounselingSessionRecord = {
  id: string;
  number: number;
  date: string;
  modality: string;
  participants: string[];
  goal: string;
  client_report: string;
  counselor_observation: string;
  interventions: string[];
  client_response: string;
  change_since_last: string;
  homework: string;
  next_plan: string;
  official_record: {
    record_type: "initial_intake" | "session_record";
    record_label: string;
    fields: Record<string, string>;
    soap: Record<string, string>;
    finalized_at: string;
  } | null;
};

export type ClientCase = ClientSummary & {
  gender: string;
  occupation: string;
  intake_date: string;
  counseling_period: string;
  referral_source: string;
  family_composition: string;
  relationship_context: string;
  presenting_problem: string;
  counseling_goals: string[];
  protective_factors: string[];
  risk_notes: string[];
  assessments: AssessmentScore[];
  questionnaire_responses: QuestionnaireResponse[];
  sessions: CounselingSessionRecord[];
  current_session_number: number;
};

export type NonverbalCue = {
  id: string;
  label: string;
  category: string;
  intensity: number;
  delay_ms: number;
  duration_ms: number;
  loop: boolean;
};

export type TurnResult = {
  turn_id: string;
  response: string;
  emotion: "neutral" | "sad" | "angry" | "anxious" | "hurt" | "withdrawn";
  emotion_intensity: number;
  nonverbal_cues: NonverbalCue[];
  supervisor_feedback: Record<string, string[] | string | number>;
  tts_text: string;
};

export type TrainingUtteranceScores = {
  empathy: number;
  open_question: number;
  nonjudgment: number;
  total: number;
};

export type TrainingCompletionResult = {
  session: {
    id: string;
    scenario_id: string;
    difficulty: string;
    goal: string;
    persona_name: string;
    persona_id: string;
    persona_gender: "female" | "male";
    status: "active" | "ended" | "completed";
  };
  completed: boolean;
  required_turns: number;
  turn_count: number;
  pre_scores: TrainingUtteranceScores | null;
  post_scores: TrainingUtteranceScores | null;
  score_change: number;
};

export type AIStatus = {
  provider: "mock" | "internal_openai" | "midm_local" | string;
  model: string;
  configured: boolean;
  reachable: boolean | null;
  detail: string;
  latency_ms: number | null;
};

export type GenerationMode = "model" | "fallback" | "mock";

export type CopilotResult = {
  provider: string;
  model: string;
  generation_mode: GenerationMode;
  fallback_reason: string | null;
  source_type: string;
  client_id?: string | null;
  session_number?: number | null;
  analysis_mode: "pre_intake" | "cumulative";
  source_scope: string[];
  summary: string;
  core_issues: string[];
  observed_emotions: string[];
  risk_signals: string[];
  recommended_directions: string[];
  suggested_questions: string[];
  recommended_phrases: string[];
  avoid_phrases: string[];
  soap_draft: Partial<Record<"S" | "O" | "A" | "P", string>>;
  module_analyses: CopilotModuleAnalysis[];
  xai_notice: string;
};

export type CopilotModuleAnalysis = {
  id: string;
  title: string;
  frameworks: string[];
  evidence_level: "사전문진 기반" | "누적기록 기반" | "확인 필요";
  summary: string;
  evidence: string[];
  hypotheses: string[];
  questions: string[];
  limitation: string;
};

export type OCRStatus = {
  provider: string;
  available: boolean;
  detail: string;
  gpu_available: boolean;
  model_id: string | null;
  review_required: boolean;
};

export type OCRToken = {
  page: string;
  mode: string;
  text: string;
  confidence: number;
};

export type OCRResult = {
  provider: string;
  raw_text: string;
  clean_text: string;
  warnings: string[];
  requires_review: boolean;
  risk_review_required: boolean;
  omission_suspected: boolean;
  review_reasons: string[];
  benchmark_notice: string;
  pages: Array<{
    page: string;
    detected_form: string;
    raw_text: string;
    clean_text: string;
    tokens: OCRToken[];
    alternate_text: string | null;
    review_reasons: string[];
    risk_terms: string[];
    omission_suspected: boolean;
  }>;
};

export type IntegratedRecords = {
  provider: string;
  model: string;
  generation_mode: GenerationMode;
  fallback_reason: string | null;
  initial_intake: Record<string, string>;
  session_record: Record<string, string>;
  soap: Partial<Record<"S" | "O" | "A" | "P", string>>;
  uncertain_items: string[];
  source_summary: Record<string, string>;
};

export type ReportResult = {
  provider: string;
  model: string;
  generation_mode: GenerationMode;
  fallback_reason: string | null;
  session_report: string;
  closing_report: string;
  review_notice: string;
};

export type SpeechStatus = {
  provider: string;
  configured: boolean;
  detail: string;
  reachable?: boolean | null;
};

export type AvatarStatus = {
  provider: "static_2d" | "longcat_http" | string;
  model?: string | null;
  configured: boolean;
  reachable: boolean | null;
  detail: string;
  latency_ms: number | null;
};

export type AvatarRenderResult = {
  turn_id: string;
  provider: string;
  emotion: TurnResult["emotion"];
  video_url: string;
  render_ms?: number | null;
};

export type DashboardRegion = {
  id: string;
  name: string;
  short_name: string;
  family_center_count: number;
  healthy_center_count: number;
  multicultural_center_count: number;
  center_count: number;
  population: number;
  households: number;
  annual_service_users_2022: number;
  map_x: number;
  map_y: number;
  counselor_count: number;
  active_clients: number;
  sessions: number;
  waitlist: number;
  utilization_rate: number;
  satisfaction: number;
  selected: boolean;
};

export type DashboardCenter = {
  id: string;
  name: string;
  region_id: string;
  region_name: string;
  center_type: string;
  counselor_count: number;
  active_clients: number;
  sessions: number;
  waitlist: number;
  avg_wait_days: number;
  utilization_rate: number;
  satisfaction: number;
  quality_score: number;
  selected: boolean;
};

export type DashboardCounselor = {
  id: string;
  display_name: string;
  center_id: string;
  center_name: string;
  region_id: string;
  employment_type: string;
  tenure_years: number;
  weekly_capacity: number;
  active_clients: number;
  utilization_rate: number;
  supervisor_eligible: boolean;
  training_completion_rate: number;
  practice_completed_sessions: number;
  practice_score_change: number | null;
  primary_specialty: string;
};

export type DashboardSummary = {
  data_as_of: string;
  period_start: string;
  period_days: number;
  scope: { type: "national" | "region" | "center"; id: string | null; label: string; region_id: string | null; center_id: string | null };
  center_count: number;
  counselor_count: number;
  active_clients: number;
  counseling_sessions: number;
  waitlist_count: number;
  avg_wait_days: number;
  utilization_rate: number;
  ai_report_minutes: number;
  satisfaction: number;
  pre_post_completion_rate: number;
  training_completion_rate: number;
  practice: {
    participating_counselors: number;
    started_sessions: number;
    completed_sessions: number;
    completion_rate: number;
    average_turns: number;
    average_score_change: number;
  };
  changes: Record<string, number>;
  regions: DashboardRegion[];
  centers: DashboardCenter[];
  counselors: DashboardCounselor[];
  issues: Array<{ issue: string; client_count: number; standard_count: number; monitor_count: number; priority_review_count: number }>;
  trend: Array<{ date: string; sessions: number; new_intakes: number; waitlist: number; utilization_rate: number; satisfaction: number }>;
  forecast: Array<{ date: string; predicted_sessions: number; lower: number; upper: number }>;
  model: {
    selected_model: string;
    validation_days: number;
    cv_folds: number;
    mae: number;
    mape: number;
    engine: string;
    ensemble_weights: Record<string, number>;
    interval_method: string;
    leaderboard: Array<{ model: string; mae: number; mape: number }>;
  };
  queue: {
    method: string;
    forecast_daily_demand: number;
    daily_slot_capacity: number;
    forecast_utilization_rate: number;
    delay_probability: number;
    current_waitlist: number;
    steady_state_queue_sessions: number;
    expected_queue_sessions: number;
    expected_wait_days: number;
    projected_backlog_after_horizon: number;
    backlog_clearance_days: number | null;
    planning_horizon_days: number;
    recommended_additional_daily_slots: number;
    pressure_level: string;
    assumption: string;
  };
  service_targets: {
    year: number;
    family_counseling_users: number;
    family_counseling_satisfaction: number;
    scope_annual_contact_target: number;
    scope_daily_contact_target: number;
    scope_monthly_contact_target: number;
    source: string;
    interpretation: string;
  };
  methodology: Record<string, string>;
};

export type SessionWorkflowItem = {
  session_number: number;
  status: "locked" | "ready" | "completed";
  required_record_type: "initial_intake" | "session_record";
  required_record_label: string;
  soap_attached: boolean;
  finalized_at: string | null;
  service_date: string | null;
};

export type SessionWorkflow = {
  client_id: string;
  next_session_number: number | null;
  total_sessions: number;
  sessions: SessionWorkflowItem[];
};
