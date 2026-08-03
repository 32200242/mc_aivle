"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import AvatarStage from "@/components/AvatarStage";
import { Panel, Tag } from "@/components/UI";
import { apiFetch, getAIStatus, getSpeechStatus, streamTrainingTurn } from "@/lib/api";
import type { AIStatus, NonverbalCue, SpeechStatus, TurnResult } from "@/lib/types";

type Session = { id: string; persona_name: string; difficulty: string; goal: string };
type Chat = { role: "counselor" | "client"; text: string };
type SpeechResultLike = { isFinal: boolean; [index: number]: { transcript: string } };
type SpeechEventLike = { results: { length: number; [index: number]: SpeechResultLike } };
type SpeechRecognitionLike = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: SpeechEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void; stop: () => void;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const emotionLabel: Record<TurnResult["emotion"], string> = {
  neutral: "차분", sad: "슬픔", angry: "분노", anxious: "불안", hurt: "상처", withdrawn: "위축",
};

function providerLabel(status: AIStatus | null) {
  if (!status) return "AI 연결 확인 중";
  if (status.provider === "mock") return "데모 응답";
  if (!status.configured) return "믿:음 설정 필요";
  if (status.reachable === false) return "믿:음 서버 오프라인";
  return `믿:음 연결 정상${status.latency_ms != null ? ` · ${status.latency_ms}ms` : ""}`;
}

export default function TrainingPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [message, setMessage] = useState("요즘 가장 힘들게 느껴지는 순간은 언제인가요?");
  const [response, setResponse] = useState("상담사의 질문을 입력하면 가상 내담자의 응답이 여기에 바로 표시됩니다.");
  const [emotion, setEmotion] = useState<TurnResult["emotion"]>("neutral");
  const [cues, setCues] = useState<NonverbalCue[]>([]);
  const [feedback, setFeedback] = useState<TurnResult["supervisor_feedback"]>({});
  const [history, setHistory] = useState<Chat[]>([]);
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState("");
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [speechStatus, setSpeechStatus] = useState<SpeechStatus | null>(null);
  const [sttSupported, setSttSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [sttError, setSttError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const speechBaseRef = useRef("");

  useEffect(() => {
    apiFetch<Session>("/training/sessions", { method: "POST", body: JSON.stringify({ scenario_id: "couple-conflict-01", difficulty: "intermediate", goal: "감정반영" }) })
      .then(setSession).catch(reason => setError(reason instanceof Error ? reason.message : "교육 세션을 만들지 못했습니다."));
    getAIStatus().then(setAIStatus).catch(() => undefined);
    getSpeechStatus().then(setSpeechStatus).catch(() => undefined);
    if (typeof window !== "undefined") {
      const speechWindow = window as typeof window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
      setSttSupported(Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition));
    }
    return () => {
      if (typeof window !== "undefined") window.speechSynthesis?.cancel();
      recognitionRef.current?.stop();
    };
  }, []);

  function toggleSTT() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const speechWindow = window as typeof window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
    const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setSttError("이 브라우저는 음성인식을 지원하지 않습니다. Chrome 또는 Edge를 사용하세요.");
      return;
    }
    setSttError("");
    speechBaseRef.current = message.trim();
    const recognition = new Recognition();
    recognition.lang = "ko-KR";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = event => {
      let finalText = "";
      let interimText = "";
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result[0]?.transcript ?? "";
        if (result.isFinal) finalText += transcript;
        else interimText += transcript;
      }
      setMessage([speechBaseRef.current, finalText, interimText].filter(Boolean).join(" ").trim());
    };
    recognition.onerror = event => {
      setSttError(event.error === "not-allowed" ? "마이크 권한이 거부되었습니다. 브라우저 주소창에서 권한을 허용하세요." : `음성인식 오류: ${event.error}`);
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function speak(data: { text: string; audio_url?: string | null }) {
    if (data.audio_url) {
      const audio = new Audio(data.audio_url);
      audio.onplay = () => setSpeaking(true);
      audio.onended = () => setSpeaking(false);
      audio.onerror = () => setSpeaking(false);
      void audio.play();
      return;
    }
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(data.text);
    utterance.lang = "ko-KR";
    utterance.rate = .92;
    utterance.pitch = .96;
    const koreanVoice = window.speechSynthesis.getVoices().find(voice => voice.lang.toLowerCase().startsWith("ko"));
    if (koreanVoice) utterance.voice = koreanVoice;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!session || !text || busy) return;
    recognitionRef.current?.stop();
    setBusy(true); setError(""); setResponse(""); setMessage("");
    setHistory(items => [...items, { role: "counselor", text }]);
    try {
      await streamTrainingTurn(session.id, text, {
        onStart: () => setResponse(""),
        onDelta: delta => setResponse(current => current + delta),
        onComplete: result => {
          setEmotion(result.emotion);
          setCues(result.nonverbal_cues);
          setFeedback(result.supervisor_feedback);
          setResponse(result.response);
          setHistory(items => [...items, { role: "client", text: result.response }]);
        },
        onTtsReady: speak,
        onError: setError,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "응답 생성에 실패했습니다.");
    } finally { setBusy(false); }
  }

  return (
    <AppShell title="AI 상담사 교육" subtitle="가상 성인 내담자 페르소나 실습 · 사례 03. 결혼 7년차 부부 갈등">
      <div className="training-toolbar"><div><Tag tone="orange">난이도 중급</Tag><span>목표: 감정 반영과 개방형 질문</span><Tag tone={aiStatus?.provider === "mock" ? "gray" : aiStatus?.reachable === false || aiStatus?.configured === false ? "orange" : "green"}>{providerLabel(aiStatus)}</Tag></div><div><span className={`live-dot ${busy ? "active" : ""}`}/>{busy ? "AI 응답 생성 중" : "실습 진행 중"}<button>일시정지</button><button className="success">저장하기</button><button className="danger">실습 종료</button></div></div>
      {aiStatus?.provider === "mock" && <div className="ai-mode-warning">현재 `.env`의 AI_PROVIDER가 mock이라 예시 응답을 사용합니다. 믿:음 서버를 연결하면 같은 화면에서 실제 생성 응답으로 자동 전환됩니다.</div>}
      {aiStatus?.provider === "internal_openai" && aiStatus.reachable === false && <div className="ai-mode-warning">{aiStatus.detail} Colab의 서버·터널 셀이 실행 중인지와 `.env` URL을 확인한 뒤 백엔드를 다시 시작하세요.</div>}
      <div className="training-layout">
        <div className="simulation-column">
          <div className="sim-card">
            <AvatarStage emotion={emotion} cues={cues} speaking={speaking} />
            <div className="persona-overlay"><b>가상 내담자 페르소나</b><span>이름　　이지은 (가명)</span><span>나이　　34세</span><span>직업　　회계원</span><span>결혼 기간　7년</span><span>자녀　　1명 (5세)</span></div>
            <div className="state-overlay"><span><small>감정 상태</small><b>{emotionLabel[emotion]} {Math.round((cues[0]?.intensity ?? .68) * 100)}%</b></span><span><small>방어적 태도</small><b>{cues.some(cue => cue.id === "posture.arms_crossed") ? "높음" : "보통"}</b></span><span><small>공감 수준</small><b>보통</b></span></div>
            <div className="emotion-tags"><span>주요 관찰 행동</span>{cues.map(cue => <Tag key={cue.id} tone="blue">{cue.label}</Tag>)}</div>
          </div>
          <form className="counselor-input" onSubmit={submit}>
            <label>상담사 발화</label><textarea value={message} onChange={event => setMessage(event.target.value)} placeholder="가상 내담자에게 질문하거나 마이크로 말해 보세요." /><button className={`stt-button ${listening ? "listening" : ""}`} type="button" onClick={toggleSTT} disabled={!sttSupported || busy} aria-pressed={listening}>{listening ? "■ 듣기 중" : "🎙 STT"}</button><button className="primary" disabled={!session || busy}>{busy ? "응답 중…" : "전송"}</button>
            <div className="stt-hint">{speechStatus?.provider === "internal_http" ? "내부망 STT 연동 준비됨" : "시연: Chrome/Edge 브라우저 STT · 운영: 내부망 STT API로 교체"}</div>
            {sttError && <p className="form-error">{sttError}</p>}
            {error && <p className="form-error">{error}</p>}
          </form>
          <div className="guidance-grid"><Panel><h3>상담 방향 추천</h3><b>☺ 공감과 이해 중심 접근</b><p>내담자의 경험을 수용하고 비판 없이 들어줍니다.</p></Panel><Panel><h3>상담 질문 추천</h3><ol><li>그 순간 어떤 감정이 가장 크게 느껴졌나요?</li><li>상대에게 바라는 점을 한 문장으로 말해볼까요?</li></ol></Panel><Panel><h3>피드백 요약</h3><b>♡ 공감 수준</b><p>{Array.isArray(feedback["보완점"]) ? feedback["보완점"][0] : "응답 후 슈퍼바이저 피드백이 표시됩니다."}</p></Panel></div>
        </div>
        <aside className="dialog-column">
          <div className="current-emotion">현재 정서: <b>{emotionLabel[emotion]} ({emotion})</b></div>
          <h3>AI 내담자 반응</h3><div className="response-box" aria-live="polite">{response}{busy && <span className="typing-caret">▍</span>}</div>
          <div className="tts-status"><span>{speaking ? "🔊 음성 재생 중 · 립싱크 적용" : "음성 대기"}</span><small>개발: 브라우저 TTS · 내부망: 사내 TTS URL로 자동 교체</small></div>
          <h3>이번 턴 비언어 행동</h3><div className="cue-list">{cues.length ? cues.map(cue => <div key={cue.id}><span>{cue.category}</span><b>{cue.label}</b><strong>{cue.intensity.toFixed(1)}</strong></div>) : <p>응답 후 행동이 표시됩니다.</p>}</div>
          <h3>대화 기록</h3><div className="chat-history">{history.slice(-6).map((item, index) => <div key={index} className={item.role}><b>{item.role === "counselor" ? "상담사" : "내담자"}</b><p>{item.text}</p></div>)}</div>
          <h3>슈퍼바이저 피드백</h3><div className="feedback-box">{Object.keys(feedback).length ? Object.entries(feedback).map(([key, value]) => <div key={key}><b>{key}</b><p>{Array.isArray(value) ? value.join(" ") : String(value)}</p></div>) : <p>첫 질문을 전송하면 즉시 생성됩니다.</p>}</div>
        </aside>
      </div>
    </AppShell>
  );
}
