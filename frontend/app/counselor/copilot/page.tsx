"use client";

import { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import RecordsWorkspace from "@/components/RecordsWorkspace";
import { Panel, Tag } from "@/components/UI";
import { analyzeClientCase, getAIStatus, getClientCase, listClients } from "@/lib/api";
import type { AIStatus, ClientCase, ClientSummary, CopilotResult, CounselingSessionRecord } from "@/lib/types";


export default function CopilotPage() {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [caseData, setCaseData] = useState<ClientCase | null>(null);
  const [sessionNumber, setSessionNumber] = useState(1);
  const [result, setResult] = useState<CopilotResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingCase, setLoadingCase] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getAIStatus().then(setStatus).catch(reason => setError(String(reason)));
    listClients()
      .then(items => {
        setClients(items);
        setSelectedClientId(current => current || items[0]?.id || "");
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "사례 목록을 불러오지 못했습니다."));
  }, []);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoadingCase(true);
    setError("");
    getClientCase(selectedClientId)
      .then(data => {
        setCaseData(data);
        setSessionNumber(data.current_session_number);
        setResult(null);
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "사례 자료를 불러오지 못했습니다."))
      .finally(() => setLoadingCase(false));
  }, [selectedClientId]);

  const selectedSession = useMemo(
    () => caseData?.sessions.find(item => item.number === sessionNumber) ?? caseData?.sessions.at(-1) ?? null,
    [caseData, sessionNumber],
  );

  const priorSessions = useMemo(
    () => caseData?.sessions.filter(item => item.number < sessionNumber) ?? [],
    [caseData, sessionNumber],
  );
  const latestPriorSession = priorSessions.at(-1) ?? null;

  const recordSource = useMemo(
    () => caseData && selectedSession ? buildRecordSource(caseData, selectedSession) : "",
    [caseData, selectedSession],
  );

  async function runAnalysis() {
    if (!caseData || !selectedSession) return;
    setBusy(true);
    setError("");
    try {
      setResult(await analyzeClientCase(caseData.id, selectedSession.number));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "코파일럿 분석에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return <AppShell title="상담 코파일럿" subtitle="내담자의 사전문진·기본정보·완료 회기기록을 불러와 다음 상담 방향을 분석합니다.">
    <div className="provider-card"><div><span className={`live-dot ${busy ? "active" : ""}`}/><b>{status?.provider === "mock" ? "데모 분석 모드" : "KT 믿:음 연결"}</b><small>{status?.model || "상태 확인 중"} · {status?.detail || "연결을 확인하고 있습니다."}</small></div><Tag tone={status?.provider === "mock" ? "gray" : !status?.configured || status?.reachable === false ? "orange" : "green"}>{!status?.configured ? "설정 필요" : status?.reachable === false ? "서버 오프라인" : status?.reachable === true ? `연결 정상${status.latency_ms != null ? ` · ${status.latency_ms}ms` : ""}` : "로드 대기"}</Tag></div>
    {status?.provider === "mock" && <div className="ai-mode-warning">현재 결과는 화면 검증용 규칙 기반 예시입니다. `.env`에서 `AI_PROVIDER=internal_openai`로 바꾸면 선택 사례 자료가 실제 믿:음 서버로 전달됩니다.</div>}
    {status?.provider === "internal_openai" && status.reachable === false && <div className="ai-mode-warning">Colab 노트북의 서버·터널 셀이 계속 실행 중인지 확인하세요. 새 ngrok URL을 `.env`에 반영했다면 FastAPI를 재시작해야 합니다.</div>}

    <Panel className="copilot-input-panel case-source-panel">
      <div className="panel-heading"><div><h2>사례 데이터 불러오기</h2><span>대화 원문을 직접 입력하지 않고 사전문진과 완료된 이전 회기 자료를 자동으로 사용합니다.</span></div><Tag tone="green">사례관리 데이터 연동</Tag></div>
      <div className="case-selector-grid">
        <label>내담자
          <select value={selectedClientId} onChange={event => setSelectedClientId(event.target.value)}>
            {clients.map(client => <option key={client.id} value={client.id}>{client.case_code} · {client.name} · {client.session_count}회기</option>)}
          </select>
        </label>
        <label>분석 기준 회기
          <select value={sessionNumber} onChange={event => { setSessionNumber(Number(event.target.value)); setResult(null); }} disabled={!caseData}>
            {caseData?.sessions.map(session => <option key={session.id} value={session.number}>{session.number}회기 준비 · {session.goal}</option>)}
          </select>
        </label>
        <button className="primary" type="button" onClick={runAnalysis} disabled={busy || loadingCase || !caseData}>{busy ? "믿:음이 상담 준비자료 분석 중…" : sessionNumber === 1 ? "사전문진으로 1회기 분석" : `누적 기록으로 ${sessionNumber}회기 분석`}</button>
      </div>

      {loadingCase && <div className="case-loading">사전문진과 회기 기록을 불러오고 있습니다.</div>}
      {caseData && selectedSession && <>
        <div className="case-identity-card">
          <span className="client-initial">{caseData.name.slice(0, 1)}</span>
          <div><small>{caseData.case_code}</small><h3>{caseData.name} <em>{caseData.age}세 · {caseData.gender} · {caseData.occupation}</em></h3><p>{caseData.primary_issue}</p></div>
          <Tag>{caseData.status}</Tag>
        </div>
        <div className="case-fact-grid">
          <div><span>상담 기간</span><b>{caseData.counseling_period}</b></div>
          <div><span>가족 구성</span><b>{caseData.family_composition}</b></div>
          <div><span>의뢰 경로</span><b>{caseData.referral_source}</b></div>
          <div><span>자동 반영 범위</span><b>기본정보 + 문진 {caseData.assessments.length}종 + 완료 회기 {priorSessions.length}건</b></div>
        </div>
        <div className="case-narrative-grid">
          <section><h3>관계·생활 맥락</h3><p>{caseData.relationship_context}</p></section>
          <section><h3>주호소 문제</h3><p>{caseData.presenting_problem}</p></section>
        </div>
        <div className="assessment-strip">
          {caseData.assessments.map(item => <article key={item.code}><small>{item.code}</small><b>{item.label}</b><strong>{item.score}/{item.max_score}</strong><Tag tone={item.severity.includes("높") || item.severity.includes("매우") ? "orange" : "gray"}>{item.severity}</Tag><p>{item.interpretation}</p></article>)}
        </div>
        <section className="session-record-preview">
          <div className="panel-heading"><div><h3>{selectedSession.number}회기 상담 준비</h3><span>선택 회기 시작 전 이용 가능한 자료만 반영</span></div><Tag>{priorSessions.length ? `이전 ${priorSessions.length}개 회기 반영` : "사전문진 기반"}</Tag></div>
          <dl>
            <div><dt>예정 회기 목표</dt><dd>{selectedSession.goal}</dd></div>
            <div><dt>분석 자료</dt><dd>{priorSessions.length ? `사전문진 ${caseData.assessments.length}종과 1~${selectedSession.number - 1}회기 완료기록` : `사전문진 ${caseData.assessments.length}종과 접수 기본정보`}</dd></div>
            {latestPriorSession ? <>
              <div><dt>직전 회기 내담자 보고</dt><dd>{latestPriorSession.client_report}</dd></div>
              <div><dt>직전 회기 상담사 관찰</dt><dd>{latestPriorSession.counselor_observation}</dd></div>
              <div><dt>직전 회기 변화</dt><dd>{latestPriorSession.change_since_last}</dd></div>
              <div><dt>직전 회기 다음 계획</dt><dd>{latestPriorSession.next_plan}</dd></div>
            </> : <>
              <div><dt>회기 기록</dt><dd>첫 회기 전이므로 완료된 상담기록을 반영하지 않습니다.</dd></div>
              <div><dt>분석 초점</dt><dd>문진 점수의 패턴, 주호소, 보호요인과 추가 확인이 필요한 위험 신호를 중심으로 초기 상담 방향을 제안합니다.</dd></div>
            </>}
          </dl>
        </section>
        <details className="case-source-details"><summary>AI에 함께 반영되는 목표·보호요인·확인사항 보기</summary><div><section><h4>상담 목표</h4>{caseData.counseling_goals.map(item => <p key={item}>• {item}</p>)}</section><section><h4>보호요인</h4>{caseData.protective_factors.map(item => <p key={item}>• {item}</p>)}</section><section><h4>위기·확인사항</h4>{caseData.risk_notes.map(item => <p key={item}>• {item}</p>)}</section></div></details>
      </>}
      {error && <p className="form-error">{error}</p>}
    </Panel>

    {result ? <div className="copilot-layout"><div>
      <Panel><div className="panel-heading"><h2>AI 상담 방향 추천</h2><Tag>{result.provider === "mock" ? "데모" : "믿:음 분석"} · {result.session_number ?? sessionNumber}회기</Tag></div><p className="analysis-summary">{result.summary}</p><div className="issue-grid"><InfoCard icon="☵" title="핵심 이슈" values={result.core_issues}/><InfoCard icon="△" title="관찰 정서" values={result.observed_emotions}/><InfoCard icon="!" title="위기·확인 신호" values={result.risk_signals}/></div><div className="recommend-grid">{result.recommended_directions.map((item, index) => <div key={item}><b>{index + 1}. 상담 방향</b><p>{item}</p></div>)}</div></Panel>
      <Panel><h2>실시간 활용 문장</h2><div className="phrase-grid"><div className="good"><b>✓ 사용 권장</b>{result.recommended_phrases.map(item => <p key={item}>“{item}”</p>)}</div><div className="bad"><b>× 사용 지양</b>{result.avoid_phrases.map(item => <p key={item}>“{item}”</p>)}</div><div className="tip"><b>다음 질문</b>{result.suggested_questions.map(item => <p key={item}>{item}</p>)}</div></div></Panel>
    </div><Panel className="report-panel"><h2>{sessionNumber === 1 ? "초기 상담 기록 초안" : "SOAP 기록 초안"}</h2><div className="report-icon">▤</div><p>선택 회기 시작 전에 이용 가능한 자료로 만든 AI 초안입니다. 상담사가 원기록과 직접 관찰을 대조한 후 확정합니다.</p><div className="soap-preview">{Object.entries(result.soap_draft).map(([key, value]) => <section key={key}><b>{key}</b><p>{value}</p></section>)}</div><button className="primary" onClick={() => navigator.clipboard?.writeText(Object.entries(result.soap_draft).map(([key,value]) => `${key}: ${value}`).join("\n"))}>기록 초안 복사</button></Panel></div>
    : <Panel className="empty-analysis"><b>내담자와 준비할 회기를 선택해 주세요.</b><p>1회기에는 사전문진과 접수정보만, 2회기부터는 직전 완료 회기까지 누적하여 상담 방향과 기록 초안을 생성합니다.</p></Panel>}

    {caseData && selectedSession && <RecordsWorkspace key={`${caseData.id}-${selectedSession.number}`} sourceText={recordSource} goal={caseData.counseling_goals.join(" / ")} note={latestPriorSession?.counselor_observation ?? ""} sourceLabel={sessionNumber === 1 ? `${caseData.case_code}의 사전문진·접수자료` : `${caseData.case_code}의 사전문진·1~${sessionNumber - 1}회기 완료기록`}/>} 
  </AppShell>;
}


function InfoCard({ icon, title, values }: { icon: string; title: string; values: string[] }) {
  return <div>{icon}<b>{title}</b>{values.map(value => <span key={value}>{value}</span>)}</div>;
}


function buildRecordSource(caseData: ClientCase, selectedSession: CounselingSessionRecord): string {
  const assessments = caseData.assessments.map(item => `${item.code} ${item.label}: ${item.score}/${item.max_score}, ${item.severity}, ${item.interpretation}`).join("\n");
  const sessions = caseData.sessions
    .filter(item => item.number < selectedSession.number)
    .map(item => `[${item.number}회기 ${item.date}]\n내담자 보고: ${item.client_report}\n상담사 관찰: ${item.counselor_observation}\n개입: ${item.interventions.join(", ")}\n반응: ${item.client_response}\n변화: ${item.change_since_last}\n다음 계획: ${item.next_plan}`)
    .join("\n\n") || "완료된 이전 회기 없음";
  return `[사례관리 자료]\n사례번호: ${caseData.case_code}\n분석 기준: ${selectedSession.number}회기 시작 전\n가족 구성: ${caseData.family_composition}\n관계 맥락: ${caseData.relationship_context}\n주호소: ${caseData.presenting_problem}\n상담 목표: ${caseData.counseling_goals.join(" / ")}\n보호요인: ${caseData.protective_factors.join(" / ")}\n확인사항: ${caseData.risk_notes.join(" / ")}\n\n[사전문진]\n${assessments}\n\n[완료된 이전 회기]\n${sessions}`;
}
