import type { AIStatus, ClientCase, ClientSummary, CopilotResult, IntegratedRecords, OCRResult, OCRStatus, ReportResult, SpeechStatus, TurnResult, User } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8100/api/v1";

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
  if (!response.ok) throw new Error((await response.json()).detail ?? "로그인에 실패했습니다.");
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
    throw new Error(body.detail ?? `API 오류 (${response.status})`);
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
    throw new Error(body.detail ?? `API 오류 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function listClients(): Promise<ClientSummary[]> {
  return apiFetch<ClientSummary[]>("/clients");
}

export async function getClientCase(clientId: string): Promise<ClientCase> {
  return apiFetch<ClientCase>(`/clients/${clientId}`);
}

type StreamHandlers = {
  onStart?: () => void;
  onDelta?: (text: string) => void;
  onComplete?: (result: TurnResult) => void;
  onTtsReady?: (data: { text: string; audio_url?: string | null; browser_speech_fallback?: boolean }) => void;
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
      if (event === "ai.error") {
        streamError = payload.message ?? "AI 응답 생성에 실패했습니다.";
        handlers.onError?.(streamError);
      }
    }
  }
  if (streamError) throw new Error(streamError);
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
  transcript: string;
  session_goal: string;
  counselor_note: string;
  ocr_text: string;
  manual_correction: string;
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

async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}
