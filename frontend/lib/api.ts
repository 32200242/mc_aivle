import type { AIStatus, AvatarRenderResult, AvatarStatus, ClientCase, ClientPage, ClientSummary, CopilotResult, IntegratedRecords, OCRResult, OCRStatus, ReportResult, SessionWorkflow, SpeechStatus, TrainingCompletionResult, TurnResult, User } from "./types";
import { HWANG_DEMO_CLIENT_ID, HWANG_NEXT_SESSION_AT } from "@/data/hwangCopilotDemo";
import { serviceDayAppointment } from "./serviceDate";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8100/api/v1";

function resolveApiMediaUrl(value: string): string {
  if (value.startsWith("http://") || value.startsWith("https://") || value.startsWith("data:")) return value;
  try {
    return new URL(value, new URL(API_BASE).origin).toString();
  } catch {
    return value;
  }
}

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("family-center-token") ?? "";
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("family-center-user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export async function login(username: string, password: string): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(apiErrorMessage(body, response.status, "로그인에 실패했습니다."));
  }
  const data = await response.json();
  localStorage.setItem("family-center-token", data.access_token);
  localStorage.setItem("family-center-user", JSON.stringify(data.user));
  return data.user as User;
}

export function logout(): void {
  localStorage.removeItem("family-center-token");
  localStorage.removeItem("family-center-user");
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (response.status === 401 && typeof window !== "undefined") {
    logout();
    window.location.href = "/login";
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(apiErrorMessage(body, response.status));
  }
  return response.json() as Promise<T>;
}

export async function apiFormFetch<T>(path: string, form: FormData): Promise<T> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { method: "POST", headers, body: form });
  if (response.status === 401 && typeof window !== "undefined") {
    logout();
    window.location.href = "/login";
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(apiErrorMessage(body, response.status));
  }
  return response.json() as Promise<T>;
}

export async function listClients(): Promise<ClientSummary[]> {
  const clients = await apiFetch<ClientSummary[]>("/clients");
  return clients.map(normalizeHwangSchedule);
}

export async function listClientsPage(page = 1, pageSize = 10, query = ""): Promise<ClientPage> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (query.trim()) params.set("q", query.trim());
  const result = await apiFetch<ClientPage>(`/clients/page?${params.toString()}`);
  return { ...result, items: result.items.map(normalizeHwangSchedule) };
}

export async function getClientCase(clientId: string): Promise<ClientCase> {
  const client = await apiFetch<ClientCase>(`/clients/${clientId}`);
  if (client.id !== HWANG_DEMO_CLIENT_ID) return client;
  const nextSessionAt = client.session_count >= 2 ? HWANG_NEXT_SESSION_AT : serviceDayAppointment(9, 0);
  const nextSessionDate = nextSessionAt.slice(0, 10);
  return {
    ...client,
    next_session_at: nextSessionAt,
    sessions: client.sessions.map(session => session.number === client.current_session_number
      ? { ...session, date: nextSessionDate }
      : session),
  };
}


function normalizeHwangSchedule(client: ClientSummary): ClientSummary {
  if (client.id !== HWANG_DEMO_CLIENT_ID) return client;
  return {
    ...client,
    next_session_at: client.session_count >= 2 ? HWANG_NEXT_SESSION_AT : serviceDayAppointment(9, 0),
  };
}

type StreamHandlers = {
  onStart?: () => void;
  onDelta?: (text: string) => void;
  onComplete?: (result: TurnResult) => void;
  onTtsReady?: (data: { text: string; audio_url?: string | null; browser_speech_fallback?: boolean; gender?: "female" | "male"; voice?: string; defer_to_avatar?: boolean }) => void;
  onAvatarRendering?: (data: { turn_id: string; emotion: TurnResult["emotion"]; message: string }) => void;
  onAvatarReady?: (data: AvatarRenderResult) => void;
  onAvatarError?: (message: string) => void;
  onError?: (message: string) => void;
};

export async function streamTrainingTurn(
  sessionId: string,
  counselorMessage: string,
  handlers: StreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE}/training/sessions/${sessionId}/turns/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ counselor_message: counselorMessage }),
  });
  if (!response.ok || !response.body) throw new Error("AI 응답 스트림을 열지 못했습니다.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamError = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      const payload = JSON.parse(data);
      if (event === "turn.started") handlers.onStart?.();
      if (event === "response.delta") handlers.onDelta?.(payload.text);
      if (event === "turn.completed") handlers.onComplete?.(payload as TurnResult);
      if (event === "tts.ready") handlers.onTtsReady?.(payload);
      if (event === "avatar.rendering") handlers.onAvatarRendering?.(payload);
      if (event === "avatar.ready") handlers.onAvatarReady?.({
        ...(payload as AvatarRenderResult),
        video_url: resolveApiMediaUrl(payload.video_url),
      });
      if (event === "avatar.error") handlers.onAvatarError?.(payload.message ?? "표현 서비스가 응답하지 않습니다.");
      if (event === "ai.error") {
        streamError = payload.message ?? "AI 응답 생성에 실패했습니다.";
        handlers.onError?.(streamError);
      }
    }
  }
  if (streamError) throw new Error(streamError);
}

export async function completeTrainingSession(sessionId: string, elapsedSeconds: number, turnCount: number): Promise<TrainingCompletionResult> {
  return apiFetch<TrainingCompletionResult>(`/training/sessions/${sessionId}/complete`, {
    method: "POST",
    body: JSON.stringify({ elapsed_seconds: elapsedSeconds, turn_count: turnCount }),
  });
}

export async function getAIStatus(): Promise<AIStatus> {
  return apiFetch<AIStatus>("/ai/status");
}

export async function analyzeCopilot(input: { transcript: string; session_goal: string; counselor_note: string }): Promise<CopilotResult> {
  return apiFetch<CopilotResult>("/copilot/analyze", { method: "POST", body: JSON.stringify(input) });
}

export async function analyzeClientCase(clientId: string, sessionNumber: number): Promise<CopilotResult> {
  return apiFetch<CopilotResult>("/copilot/analyze-case", {
    method: "POST",
    body: JSON.stringify({ client_id: clientId, session_number: sessionNumber }),
  });
}

export async function getSessionWorkflow(clientId: string): Promise<SessionWorkflow> {
  return apiFetch<SessionWorkflow>(`/documents/workflow/${clientId}`);
}

export async function finalizeSessionRecord(
  clientId: string,
  sessionNumber: number,
  records: IntegratedRecords,
  includeSoap: boolean,
  soapSourceLabel: string,
  serviceDate: string,
): Promise<SessionWorkflow> {
  return apiFetch<SessionWorkflow>(`/documents/workflow/${clientId}/sessions/${sessionNumber}/finalize`, {
    method: "POST",
    body: JSON.stringify({ records, include_soap: includeSoap, soap_source_label: soapSourceLabel, service_date: serviceDate }),
  });
}

export async function getOCRStatus(): Promise<OCRStatus> {
  return apiFetch<OCRStatus>("/documents/ocr/status");
}

export async function runOCR(files: File[], preprocessMode: string, formHint: string, useGpu: boolean): Promise<OCRResult> {
  const documents = await Promise.all(files.map(async file => ({
    filename: file.name,
    content_type: file.type || "application/octet-stream",
    data_base64: await fileToBase64(file),
  })));
  return apiFetch<OCRResult>("/documents/ocr", {
    method: "POST",
    body: JSON.stringify({ documents, preprocess_mode: preprocessMode, form_hint: formHint, use_gpu: useGpu }),
  });
}

export type RecordGenerateInput = {
  record_type: "initial_intake" | "session_record";
  include_soap: boolean;
  client_id: string;
  session_number: number;
  transcript: string;
  session_goal: string;
  counselor_note: string;
  ocr_text: string;
  manual_correction: string;
  ocr_reviewed: boolean;
  ocr_review_note: string;
  ocr_review_flags: string[];
  existing_summary: string;
  form_hint: string;
};

export async function generateIntegratedRecords(input: RecordGenerateInput): Promise<IntegratedRecords> {
  return apiFetch<IntegratedRecords>("/documents/records/generate", { method: "POST", body: JSON.stringify(input) });
}

export async function generateCaseReport(input: {
  records: IntegratedRecords;
  case_summary: string;
  session_change: string;
  goal_status: string;
  next_date: string;
}): Promise<ReportResult> {
  return apiFetch<ReportResult>("/documents/reports/generate", { method: "POST", body: JSON.stringify(input) });
}

export async function getSpeechStatus(): Promise<SpeechStatus> {
  return apiFetch<SpeechStatus>("/speech/status");
}

export async function transcribeSpeech(audio: Blob, filename = "counselor-speech.webm"): Promise<{ text: string; provider: string }> {
  const headers = new Headers({
    "Content-Type": audio.type || "audio/webm",
    "X-Filename": filename,
  });
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}/speech/transcribe`, { method: "POST", headers, body: audio });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(apiErrorMessage(body, response.status, "음성을 인식하지 못했습니다."));
  }
  return response.json() as Promise<{ text: string; provider: string }>;
}

export async function getAvatarStatus(): Promise<AvatarStatus> {
  return apiFetch<AvatarStatus>("/avatar/status");
}

async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}

function apiErrorMessage(body: unknown, status: number, fallback?: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return userFacingError(detail, fallback);
    if (Array.isArray(detail)) {
      const messages = detail.map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg?: unknown }).msg ?? "");
        }
        return typeof item === "string" ? item : JSON.stringify(item);
      }).filter(Boolean);
      if (messages.length) return userFacingError(messages.join(" · "), fallback);
    }
  }
  return fallback ?? (status >= 500 ? "서비스 연결 상태를 확인한 후 다시 시도해 주세요." : "요청을 처리하지 못했습니다. 입력 내용을 확인해 주세요.");
}

function userFacingError(detail: string, fallback?: string): string {
  const technicalPattern = /(?:\.env|ngrok|fastapi|colab|localhost|127\.0\.0\.1|internal_openai|ai_provider|token_type_ids|traceback|http\s*\d{3}|model_kwargs|cuda|gpu)/i;
  return technicalPattern.test(detail)
    ? fallback ?? "서비스 연결 상태를 확인한 후 다시 시도해 주세요."
    : detail;
}
