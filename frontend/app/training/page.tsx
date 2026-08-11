"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import AvatarStage from "@/components/AvatarStage";
import { Panel } from "@/components/UI";
import { apiFetch, getSpeechStatus, streamTrainingTurn } from "@/lib/api";
import type { NonverbalCue, SpeechStatus, TurnResult } from "@/lib/types";


type Session = {
  id: string;
  scenario_id: string;
  persona_name: string;
  persona_id: "lee-jieun" | "kim-minseok";
  persona_gender: "female" | "male";
  difficulty: string;
  goal: string;
  status: "active" | "ended" | "completed";
};
type PersonaId = Session["persona_id"];
type Chat = { role: "counselor" | "client"; text: string };
type SpeechPayload = {
  text: string;
  audio_url?: string | null;
  defer_to_avatar?: boolean;
};
type SpeechResultLike = { isFinal: boolean; [index: number]: { transcript: string } };
type SpeechEventLike = { results: { length: number; [index: number]: SpeechResultLike } };
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;


const FIRST_QUESTION = "요즘 가장 힘들게 느껴지는 순간은 언제인가요?";
const FIRST_RESPONSE_VIDEO = "/training/lee-jieun-counselor-training-final.mp4";
const PERSONAS: Record<PersonaId, {
  name: string;
  gender: string;
  age: number;
  occupation: string;
  marriagePeriod: string;
  children: string;
  partner: string;
}> = {
  "lee-jieun": { name: "이지은 (가명)", gender: "여성", age: 34, occupation: "회계원", marriagePeriod: "7년", children: "1명 (5세)", partner: "남편" },
  "kim-minseok": { name: "김민석 (가명)", gender: "남성", age: 42, occupation: "영업관리직", marriagePeriod: "7년", children: "1명 (5세)", partner: "아내" },
};
const emotionLabel: Record<TurnResult["emotion"], string> = {
  neutral: "차분",
  sad: "슬픔",
  angry: "분노",
  anxious: "불안",
  hurt: "상처",
  withdrawn: "위축",
};


function isFirstQuestion(text: string) {
  const normalize = (value: string) => value.replace(/\s+/g, "").replace(/[?？.!。]+$/, "");
  return normalize(text) === normalize(FIRST_QUESTION);
}


function firstFeedbackLine(feedback: TurnResult["supervisor_feedback"]) {
  const value = feedback["보완점"];
  if (Array.isArray(value)) return value[0] ?? "다음 발화를 입력해 실습을 이어가세요.";
  if (typeof value === "string") return value;
  return "응답 후 슈퍼바이저 피드백이 표시됩니다.";
}


export default function TrainingPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [selectedPersonaId, setSelectedPersonaId] = useState<PersonaId>("lee-jieun");
  const [autoPlayAudio, setAutoPlayAudio] = useState(true);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [message, setMessage] = useState(FIRST_QUESTION);
  const [response, setResponse] = useState("상담사의 질문을 입력하면 가상 내담자의 응답이 여기에 표시됩니다.");
  const [emotion, setEmotion] = useState<TurnResult["emotion"]>("neutral");
  const [emotionIntensity, setEmotionIntensity] = useState(.55);
  const [cues, setCues] = useState<NonverbalCue[]>([]);
  const [feedback, setFeedback] = useState<TurnResult["supervisor_feedback"]>({});
  const [history, setHistory] = useState<Chat[]>([]);
  const [turnCount, setTurnCount] = useState(0);
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [avatarRendering, setAvatarRendering] = useState(false);
  const [avatarVideoUrl, setAvatarVideoUrl] = useState<string | null>(null);
  const [avatarVideoPlaybackKey, setAvatarVideoPlaybackKey] = useState(0);
  const [avatarNotice, setAvatarNotice] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [speechStatus, setSpeechStatus] = useState<SpeechStatus | null>(null);
  const [sttSupported, setSttSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [sttError, setSttError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const speechBaseRef = useRef("");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const pendingSpeechRef = useRef<SpeechPayload | null>(null);
  const needsVideoSpeechFallbackRef = useRef(false);
  const fixedFirstVideoRef = useRef(false);

  useEffect(() => {
    void startPractice("lee-jieun", false);
    getSpeechStatus().then(setSpeechStatus).catch(() => undefined);
    if (typeof window !== "undefined") {
      const speechWindow = window as typeof window & {
        SpeechRecognition?: SpeechRecognitionConstructor;
        webkitSpeechRecognition?: SpeechRecognitionConstructor;
      };
      setSttSupported(Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition));
    }
    return () => {
      if (typeof window !== "undefined") window.speechSynthesis?.cancel();
      recognitionRef.current?.stop();
      audioRef.current?.pause();
    };
  }, []);

  function toggleSTT() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const speechWindow = window as typeof window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
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
      setSttError(event.error === "not-allowed"
        ? "마이크 권한이 거부되었습니다. 브라우저 주소창에서 권한을 허용하세요."
        : `음성인식 오류: ${event.error}`);
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function stopSpeech() {
    audioRef.current?.pause();
    audioRef.current = null;
    if (typeof window !== "undefined") window.speechSynthesis?.cancel();
    setSpeaking(false);
  }

  function speak(data: SpeechPayload) {
    stopSpeech();
    if (data.audio_url) {
      const audio = new Audio(data.audio_url);
      audioRef.current = audio;
      audio.onplay = () => setSpeaking(true);
      audio.onended = () => setSpeaking(false);
      audio.onerror = () => setSpeaking(false);
      void audio.play().catch(() => setSpeaking(false));
      return;
    }
    if (!("speechSynthesis" in window)) return;
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

  function handleTtsReady(data: SpeechPayload) {
    pendingSpeechRef.current = data;
    if (!autoPlayAudio) return;
    if (fixedFirstVideoRef.current) {
      if (needsVideoSpeechFallbackRef.current) speak(data);
      return;
    }
    if (!data.defer_to_avatar || needsVideoSpeechFallbackRef.current) speak(data);
  }

  function handleVideoStart(usingEmbeddedAudio: boolean) {
    setAvatarRendering(false);
    if (!autoPlayAudio) {
      stopSpeech();
      return;
    }
    if (usingEmbeddedAudio) {
      needsVideoSpeechFallbackRef.current = false;
      stopSpeech();
      setSpeaking(true);
      return;
    }
    needsVideoSpeechFallbackRef.current = true;
    if (pendingSpeechRef.current) speak(pendingSpeechRef.current);
  }

  function handleVideoEnd() {
    setSpeaking(false);
    needsVideoSpeechFallbackRef.current = false;
  }

  function handleVideoError() {
    setAvatarRendering(false);
    setAvatarNotice("영상을 재생하지 못해 음성과 기본 표정으로 계속합니다.");
    needsVideoSpeechFallbackRef.current = true;
    if (autoPlayAudio && pendingSpeechRef.current) speak(pendingSpeechRef.current);
  }

  async function startPractice(personaId: PersonaId, announce = true) {
    if (sessionLoading && session) return;
    recognitionRef.current?.stop();
    stopSpeech();
    setSessionLoading(true);
    setError("");
    setSttError("");
    setMessage(FIRST_QUESTION);
    setResponse("상담사의 질문을 입력하면 가상 내담자의 응답이 여기에 표시됩니다.");
    setEmotion("neutral");
    setEmotionIntensity(.55);
    setCues([]);
    setFeedback({});
    setHistory([]);
    setTurnCount(0);
    setAvatarRendering(false);
    setAvatarVideoUrl(null);
    setAvatarVideoPlaybackKey(0);
    setAvatarNotice("");
    pendingSpeechRef.current = null;
    fixedFirstVideoRef.current = false;
    needsVideoSpeechFallbackRef.current = false;
    try {
      const created = await apiFetch<Session>("/training/sessions", {
        method: "POST",
        body: JSON.stringify({
          scenario_id: "couple-conflict-01",
          difficulty: "intermediate",
          goal: "감정반영",
          persona_id: personaId,
        }),
      });
      setSession(created);
      setSelectedPersonaId(personaId);
      setNotice(announce ? "선택한 설정으로 새 실습을 시작했습니다." : "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "교육 세션을 만들지 못했습니다.");
    } finally {
      setSessionLoading(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!session || !text || busy || sessionLoading) return;
    const fixedFirstTurn = history.length === 0 && session.persona_id === "lee-jieun" && isFirstQuestion(text);
    fixedFirstVideoRef.current = fixedFirstTurn;
    needsVideoSpeechFallbackRef.current = false;
    pendingSpeechRef.current = null;
    recognitionRef.current?.stop();
    stopSpeech();
    setBusy(true);
    setError("");
    setNotice("");
    setResponse("");
    setMessage("");
    setAvatarNotice("");
    setAvatarRendering(false);
    setAvatarVideoUrl(null);
    setHistory(items => [...items, { role: "counselor", text }]);
    try {
      await streamTrainingTurn(session.id, text, {
        onStart: () => setResponse(""),
        onDelta: delta => setResponse(current => current + delta),
        onComplete: result => {
          setEmotion(result.emotion);
          setEmotionIntensity(result.emotion_intensity);
          setCues(result.nonverbal_cues);
          setFeedback(result.supervisor_feedback);
          setResponse(result.response);
          setHistory(items => [...items, { role: "client", text: result.response }]);
          setTurnCount(count => count + 1);
          if (fixedFirstTurn) {
            setAvatarVideoUrl(FIRST_RESPONSE_VIDEO);
            setAvatarVideoPlaybackKey(key => key + 1);
          }
        },
        onTtsReady: handleTtsReady,
        onAvatarRendering: () => {
          if (fixedFirstTurn) return;
          setAvatarRendering(true);
          setAvatarVideoUrl(null);
        },
        onAvatarReady: result => {
          if (fixedFirstTurn) return;
          setAvatarRendering(false);
          setAvatarVideoUrl(result.video_url);
        },
        onAvatarError: messageValue => {
          if (fixedFirstTurn) return;
          setAvatarRendering(false);
          setAvatarNotice(messageValue);
          needsVideoSpeechFallbackRef.current = true;
          if (autoPlayAudio && pendingSpeechRef.current) speak(pendingSpeechRef.current);
        },
        onError: setError,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "응답 생성에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  function replayResponse() {
    if (!response.trim() || busy) return;
    if (fixedFirstVideoRef.current) {
      setAvatarVideoPlaybackKey(key => key + 1);
      return;
    }
    speak(pendingSpeechRef.current ?? { text: response });
  }

  const activePersonaId = session?.persona_id ?? "lee-jieun";
  const activePersona = PERSONAS[activePersonaId];
  const selectedPersona = PERSONAS[selectedPersonaId];
  const personaName = session?.persona_name ?? activePersona.name;

  return (
    <AppShell title="AI 상담사 교육" subtitle="가상 성인 내담자 페르소나 실습 · 사례 03. 결혼 7년차 부부 갈등">
      <section className="scenario-card">
        <div className="scenario-controls">
          <label>내담자 페르소나
            <select value={selectedPersonaId} onChange={event => setSelectedPersonaId(event.target.value as PersonaId)} disabled={sessionLoading || busy}>
              <option value="lee-jieun">이지은 (가명) · 여성</option>
              <option value="kim-minseok">김민석 (가명) · 남성</option>
            </select>
          </label>
          <label>사례 유형<select defaultValue="couple-conflict"><option value="couple-conflict">부부 갈등</option></select></label>
          <label>난이도<select defaultValue="intermediate"><option value="intermediate">중급</option></select></label>
          <label>훈련 목표<select defaultValue="emotion-reflection"><option value="emotion-reflection">감정반영</option></select></label>
          <label className="auto-tts"><input type="checkbox" checked={autoPlayAudio} onChange={event => setAutoPlayAudio(event.target.checked)}/> 응답 음성 자동 재생</label>
        </div>
        <div className="scenario-copy">
          <span className="scenario-kicker">상황 카드</span>
          <h2>사례 03. 결혼 7년차 부부 갈등</h2>
          <p>결혼 7년 차 부부로 5세 자녀가 있습니다. 생활비와 육아 분담 문제로 갈등이 반복되고, 대화를 시작하면 방어와 비난으로 번집니다.</p>
          <blockquote><b>내담자 첫 호소</b>요즘 {selectedPersona.partner}이랑 대화만 시작하면 결국 싸움으로 끝나요. 제가 무슨 말을 해도 공격적으로 받아들이는 것 같아요.</blockquote>
          <small>상담자가 탐색할 욕구: 존중받는 느낌, 안전한 대화, 감정적으로 무시당하지 않는 경험</small>
        </div>
        <div className="scenario-actions">
          <button className="primary" type="button" onClick={() => void startPractice(selectedPersonaId)} disabled={sessionLoading || busy}>{sessionLoading ? "실습 준비 중…" : "설정 적용·새 실습"}</button>
          <button type="button" onClick={() => void startPractice(activePersonaId)} disabled={sessionLoading || busy}>대화 초기화</button>
          <span>{turnCount}턴 진행</span>
        </div>
      </section>
      {notice && <div className="training-notice">{notice}</div>}
      <div className="training-layout">
        <div className="simulation-column">
          <div className="sim-card">
            <AvatarStage
              personaId={session?.persona_id ?? "lee-jieun"}
              personaName={personaName}
              emotion={emotion}
              videoUrl={avatarVideoUrl}
              preloadVideoUrl={FIRST_RESPONSE_VIDEO}
              playbackKey={avatarVideoPlaybackKey}
              rendering={avatarRendering}
              speaking={speaking}
              preferEmbeddedAudio={autoPlayAudio}
              onVideoStart={handleVideoStart}
              onVideoEnd={handleVideoEnd}
              onVideoError={handleVideoError}
            />
            <div className="persona-overlay"><b>가상 내담자 페르소나</b><span>이름　　{personaName}</span><span>성별　　{activePersona.gender}</span><span>나이　　{activePersona.age}세</span><span>직업　　{activePersona.occupation}</span><span>결혼 기간　{activePersona.marriagePeriod}</span><span>자녀　　{activePersona.children}</span></div>
            <div className="state-overlay"><span><small>감정 상태</small><b>{emotionLabel[emotion]} {Math.round(emotionIntensity * 100)}%</b></span><span><small>현재 표정</small><b>{avatarRendering ? "준비 중" : "표정 반영"}</b></span><span><small>입모양</small><b>{speaking ? "말하는 중" : "대기"}</b></span></div>
          </div>
          <form className="counselor-input" onSubmit={submit}>
            <label>상담사 발화</label><textarea value={message} onChange={event => setMessage(event.target.value)} placeholder="가상 내담자에게 질문하거나 마이크로 말해 보세요." disabled={busy || sessionLoading}/><button className={`stt-button ${listening ? "listening" : ""}`} type="button" onClick={toggleSTT} disabled={!sttSupported || busy || sessionLoading} aria-pressed={listening}>{listening ? "■ 듣기 중" : "🎙 음성 입력"}</button><button className="primary" disabled={!session || busy || sessionLoading}>{busy ? "응답 중…" : "전송"}</button>
            {sttError && <p className="form-error">{sttError}</p>}
            {error && <p className="form-error">{error}</p>}
          </form>
          <div className="guidance-grid"><Panel><h3>상담 방향 추천</h3><b>☺ 공감과 이해 중심 접근</b><p>내담자의 경험을 수용하고 비판 없이 들어줍니다.</p></Panel><Panel><h3>상담 질문 추천</h3><ol><li>그 순간 어떤 감정이 가장 크게 느껴졌나요?</li><li>상대에게 바라는 점을 한 문장으로 말해볼까요?</li></ol></Panel><Panel><h3>피드백 요약</h3><b>♡ 공감 수준</b><p>{firstFeedbackLine(feedback)}</p></Panel></div>
        </div>
        <aside className="dialog-column">
          <h3>내담자 반응</h3><div className="response-box" aria-live="polite">{response}{busy && <span className="typing-caret">▍</span>}</div>
          <div className="tts-status"><span>{avatarRendering ? "표정·입모양 준비 중" : speaking ? "🔊 응답 재생 중" : autoPlayAudio ? "자동 음성 대기" : "자동 음성 꺼짐"}</span><small>응답 음성과 표정이 아바타 화면에서 함께 재생됩니다.</small><button type="button" onClick={replayResponse} disabled={!history.some(item => item.role === "client") || busy}>최근 응답 다시 듣기</button></div>
          {avatarNotice && <p className="training-pending">{avatarNotice}</p>}
          <h3>페르소나 상태</h3><div className="avatar-info-grid"><div><span>표정</span><b>{emotionLabel[emotion]}</b></div><div><span>강도</span><b>{Math.round(emotionIntensity * 100)}%</b></div><div className="wide"><span>표현 상태</span><b>{avatarRendering ? "표정과 입모양을 준비하고 있습니다." : speaking ? "내담자 응답을 재생하고 있습니다." : "페르소나 표정이 준비되어 있습니다."}</b></div></div>
          <h3>대화 기록</h3><div className="chat-history">{history.length ? history.slice(-6).map((item, index) => <div key={`${item.role}-${index}`} className={item.role}><b>{item.role === "counselor" ? "상담사" : "내담자"}</b><p>{item.text}</p></div>) : <p className="empty-chat">첫 질문을 전송하면 상담사와 내담자의 대화가 차례로 기록됩니다.</p>}</div>
          <h3>슈퍼바이저 피드백</h3><div className="feedback-box">{Object.keys(feedback).length ? Object.entries(feedback).map(([key, value]) => <div key={key}><b>{key}</b><p>{Array.isArray(value) ? value.join(" ") : String(value)}</p></div>) : <p>첫 질문을 전송하면 즉시 생성됩니다.</p>}</div>
        </aside>
      </div>
    </AppShell>
  );
}
