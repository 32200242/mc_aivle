export type Role = "central_admin" | "center_admin" | "counselor" | "trainer";

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

export type AssessmentScore = {
  code: string;
  label: string;
  score: number;
  max_score: number;
  severity: string;
  interpretation: string;
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

export type AIStatus = {
  provider: "mock" | "internal_openai" | "midm_local" | string;
  model: string;
  configured: boolean;
  reachable: boolean | null;
  detail: string;
  latency_ms: number | null;
};

export type CopilotResult = {
  provider: string;
  model: string;
  source_type: string;
  client_id?: string | null;
  session_number?: number | null;
  summary: string;
  core_issues: string[];
  observed_emotions: string[];
  risk_signals: string[];
  recommended_directions: string[];
  suggested_questions: string[];
  recommended_phrases: string[];
  avoid_phrases: string[];
  soap_draft: Record<"S" | "O" | "A" | "P", string>;
};

export type OCRStatus = {
  provider: string;
  available: boolean;
  detail: string;
  gpu_available: boolean;
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
  pages: Array<{
    page: string;
    detected_form: string;
    raw_text: string;
    clean_text: string;
    tokens: OCRToken[];
  }>;
};

export type IntegratedRecords = {
  provider: string;
  model: string;
  initial_intake: Record<string, string>;
  session_record: Record<string, string>;
  soap: Record<"S" | "O" | "A" | "P", string>;
  uncertain_items: string[];
  source_summary: Record<string, string>;
};

export type ReportResult = {
  provider: string;
  model: string;
  session_report: string;
  closing_report: string;
  review_notice: string;
};

export type SpeechStatus = {
  provider: string;
  configured: boolean;
  detail: string;
};
