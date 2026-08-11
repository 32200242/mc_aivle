"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import AppShell from "@/components/AppShell";
import RecordsWorkspace from "@/components/RecordsWorkspace";
import { Panel, Tag } from "@/components/UI";
import { HWANG_COPILOT_RESULT, HWANG_DEMO_CLIENT_ID } from "@/data/hwangCopilotDemo";
import { analyzeClientCase, getAIStatus, getClientCase, getSessionWorkflow, listClients } from "@/lib/api";
import { serviceDateInSeoul } from "@/lib/serviceDate";
import type { AIStatus, ClientCase, ClientSummary, CopilotResult, SessionWorkflow } from "@/lib/types";


export default function CopilotPage() {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [caseData, setCaseData] = useState<ClientCase | null>(null);
  const [workflow, setWorkflow] = useState<SessionWorkflow | null>(null);
  const [sessionNumber, setSessionNumber] = useState(1);
  const [result, setResult] = useState<CopilotResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingCase, setLoadingCase] = useState(true);
  const [error, setError] = useState("");
  const [activeStep, setActiveStep] = useState(1);
  const [maxStep, setMaxStep] = useState(1);

  useEffect(() => {
    listClients()
      .then(items => {
        setClients(items);
        const preparedCase = items.find(item => item.id === HWANG_DEMO_CLIENT_ID);
        const requestedClientId = new URLSearchParams(window.location.search).get("client");
        const requestedCase = items.find(item => item.id === requestedClientId);
        setSelectedClientId(current => current || requestedCase?.id || preparedCase?.id || items[0]?.id || "");
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "사례 목록을 불러오지 못했습니다."));
  }, []);

  useEffect(() => {
    if (!selectedClientId) return;
    if (selectedClientId === HWANG_DEMO_CLIENT_ID && sessionNumber === 2) {
      setStatus({
        provider: "prepared_case",
        model: "prepared_case",
        configured: true,
        reachable: true,
        detail: "상담 준비자료를 불러왔습니다.",
        latency_ms: 0,
      });
      return;
    }
    getAIStatus().then(setStatus).catch(reason => setError(String(reason)));
  }, [selectedClientId, sessionNumber]);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoadingCase(true);
    setError("");
    Promise.all([getClientCase(selectedClientId), getSessionWorkflow(selectedClientId)])
      .then(([data, workflowData]) => {
        setCaseData(data);
        setWorkflow(workflowData);
        setSessionNumber(workflowData.next_session_number ?? workflowData.total_sessions);
        setResult(null);
        setActiveStep(1);
        setMaxStep(1);
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "사례 자료를 불러오지 못했습니다."))
      .finally(() => setLoadingCase(false));
  }, [selectedClientId]);

  const selectedSession = useMemo(
    () => caseData?.sessions.find(item => item.number === sessionNumber) ?? null,
    [caseData, sessionNumber],
  );

  const priorSessions = useMemo(
    () => caseData?.sessions.filter(item => item.number < sessionNumber) ?? [],
    [caseData, sessionNumber],
  );
  const aiAssessments = useMemo(
    () => caseData?.assessments.filter(item => !item.code.startsWith("BFI10")) ?? [],
    [caseData],
  );
  const firstSession = sessionNumber === 1;
  const preparedCase = selectedClientId === HWANG_DEMO_CLIENT_ID && sessionNumber === 2;
  const preparedServiceDate = serviceDateInSeoul();
  const selectedWorkflow = workflow?.sessions.find(item => item.session_number === sessionNumber) ?? null;
  const serviceState = preparedCase
    ? "online"
    : !status
    ? "loading"
    : status.provider === "mock" || !status.configured || status.reachable === false
      ? "offline"
      : status.reachable === true
        ? "online"
        : "loading";

  async function runAnalysis() {
    if (!caseData || !selectedSession) return;
    if (preparedCase) {
      setResult(HWANG_COPILOT_RESULT);
      setError("");
      return;
    }
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

  function moveToStep(step: number) {
    setActiveStep(step);
    setMaxStep(current => Math.max(current, step));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return <AppShell title="상담 코파일럿" subtitle="현재 상담을 준비·분석하고 상담기록을 작성·확정합니다.">
    <div className="service-status-row" aria-live="polite">
      <span className="compact-status"><i className={`service-dot ${serviceState}`}/>{serviceState === "online" ? "분석 서비스 정상" : serviceState === "offline" ? "분석 서비스 확인 필요" : "분석 서비스 확인 중"}</span>
    </div>
    {!preparedCase && serviceState === "offline" && <div className="service-connection-note">분석 서비스 연결을 확인해 주세요.</div>}

    <CopilotStepper activeStep={activeStep} maxStep={maxStep} onStepChange={setActiveStep}/>
    <div className="copilot-deck-layout">
      <main className="copilot-main-deck">

    {activeStep === 1 && <Panel className="copilot-input-panel case-source-panel workflow-deck-card">
      <div className="workflow-card-kicker">1단계 · 사례 선택</div>
      <div className="panel-heading"><div><h2>준비할 사례와 회기를 선택하세요</h2><span>선택한 사례의 일정, 목표와 분석 범위를 먼저 확인합니다.</span></div><Tag tone="green">사례관리 연결</Tag></div>
      <div className="case-selector-grid">
        <label>내담자
          <select value={selectedClientId} onChange={event => setSelectedClientId(event.target.value)}>
            {clients.map(client => <option key={client.id} value={client.id}>{client.case_code} · {client.name} · {client.session_count}회기</option>)}
          </select>
        </label>
        <label>분석 기준 회기
          <select value={sessionNumber} onChange={event => { setSessionNumber(Number(event.target.value)); setResult(null); setMaxStep(1); }} disabled={!caseData || preparedCase}>
            {caseData?.sessions.map(session => {
              const state = workflow?.sessions.find(item => item.session_number === session.number);
              const stateLabel = state?.status === "completed" ? "완료" : state?.status === "ready" ? "작성 가능" : "이전 기록 확정 필요";
              return <option key={session.id} value={session.number} disabled={state?.status === "locked"}>{session.number}회기 · {stateLabel}</option>;
            })}
          </select>
        </label>
        <button className="primary" type="button" onClick={() => moveToStep(2)} disabled={loadingCase || !caseData}>선택 완료 · 분석으로 →</button>
      </div>

      {loadingCase && <div className="case-loading">사전문진과 회기 기록을 불러오고 있습니다.</div>}
      {caseData && selectedSession && <>
        <div className="case-identity-card">
          <span className="client-initial">{caseData.name.slice(0, 1)}</span>
          <div><small>{caseData.case_code}</small><h3>{caseData.name}</h3><p>{firstSession ? "1회기 전 사전문진 검토" : caseData.primary_issue}</p></div>
          <div className="case-summary-actions"><Tag>{selectedWorkflow?.status === "completed" ? "기록 확정" : firstSession ? "1회기 준비" : `${sessionNumber}회기 준비`}</Tag><Link href={`/counselor/clients/${caseData.id}`}>사례 전체 보기 →</Link></div>
        </div>
        <div className="case-fact-grid copilot-session-facts">
          <div><span>현재 일정</span><b>{preparedCase ? formatPreparedSchedule(preparedServiceDate) : formatCaseSchedule(caseData.next_session_at, selectedSession.date)}</b></div>
          <div><span>이번 회기 목표</span><b>{selectedSession.goal}</b></div>
          <div><span>핵심 이슈</span><b>{caseData.primary_issue}</b></div>
          <div><span>분석 범위</span><b>{firstSession ? `사전문진 ${aiAssessments.length}종` : `사전문진 ${aiAssessments.length}종 + 확정 회기 ${priorSessions.length}건`}</b></div>
        </div>
        <details className="case-source-details copilot-source-summary"><summary>분석에 사용되는 사례 근거 요약</summary><div>
          <section><h4>사전문진</h4><p>{aiAssessments.map(item => `${item.code} ${item.score}/${item.max_score}`).join(" · ") || "자료 없음"}</p></section>
          <section><h4>확정 기록</h4><p>{firstSession ? "첫 회기 전 · 반영 기록 없음" : workflow?.sessions.filter(item => item.status === "completed" && item.session_number < sessionNumber).map(item => `${item.session_number}회기`).join(" · ") || "없음"}</p></section>
          <section><h4>안전·확인사항</h4><p>{caseData.risk_notes.slice(0, 2).join(" · ") || "기록 없음"}</p></section>
        </div></details>
      </>}
      {error && <p className="form-error">{error}</p>}
      <WorkflowNav step={1} onNext={() => moveToStep(2)} nextDisabled={loadingCase || !caseData} nextLabel="다음: 분석"/>
    </Panel>}

    {activeStep === 2 && <Panel className="analysis-launch-card workflow-deck-card">
      <div className="workflow-card-kicker">2단계 · 분석</div>
      <div className="panel-heading"><div><h2>{caseData?.name ?? "선택 사례"} {sessionNumber}회기 준비 분석</h2><span>사전문진과 확정된 이전 회기 기록을 바탕으로 상담 초점을 정리합니다.</span></div><Tag tone="green">근거</Tag></div>
      <div className="analysis-launch-summary"><div><span>분석 대상</span><b>{caseData?.case_code} · {caseData?.name}</b></div><div><span>이번 회기 목표</span><b>{selectedSession?.goal ?? "-"}</b></div><div><span>사용 자료</span><b>{firstSession ? `사전문진 ${aiAssessments.length}종` : `사전문진 ${aiAssessments.length}종 + 확정 회기 ${priorSessions.length}건`}</b></div></div>
      <button className="primary wide" type="button" onClick={runAnalysis} disabled={busy || loadingCase || !caseData}>{busy ? "상담 준비자료 분석 중…" : preparedCase ? result ? "2회기 분석 다시 실행" : "2회기 분석 실행" : sessionNumber === 1 ? "사전문진으로 1회기 분석" : `누적 기록으로 ${sessionNumber}회기 분석`}</button>
    </Panel>}

    {activeStep === 2 && (result ? <>
      <Panel className="module-analysis-panel">
        <div className="panel-heading"><div><h2>{result.analysis_mode === "pre_intake" ? "사전문진 분석" : "누적자료 분석"}</h2><span>{result.source_scope.join(" · ")}만 근거로 사용</span></div><Tag tone="green">근거 확인</Tag></div>
        <p className="analysis-summary">{result.summary}</p>
        <div className="xai-notice"><b>분석 기준</b><span>{result.source_scope.join(" · ")}에 기록된 내용과 점수를 기준으로 정리했습니다.</span></div>
        <div className="module-analysis-grid">{result.module_analyses.map(module => <article key={module.id}>
          <header><div><small>{module.evidence_level}</small><h3>{module.title}</h3></div><Tag>{module.frameworks.join(" · ")}</Tag></header>
          <p>{module.summary}</p>
          <details open={module.id === "intake_pattern" || module.id === "safety_priority"}><summary>근거와 해석 과정</summary>
            <div className="module-evidence"><section><b>사용 근거</b>{module.evidence.map(item => <span key={item}>• {item}</span>)}</section><section><b>확인할 가설</b>{module.hypotheses.map(item => <span key={item}>• {item}</span>)}</section></div>
            <section className="module-questions"><b>면담 확인 질문</b>{module.questions.map(item => <span key={item}>• {item}</span>)}</section>
          </details>
        </article>)}</div>
      </Panel>
      <div className="copilot-layout"><div>
        <Panel><div className="panel-heading"><h2>{firstSession ? "첫 면담 확인 초점" : "상담 방향"}</h2><Tag>{result.session_number ?? sessionNumber}회기 준비</Tag></div><div className="issue-grid"><InfoCard icon="☵" title={firstSession ? "문진상 확인 영역" : "핵심 이슈"} values={result.core_issues}/><InfoCard icon="△" title={firstSession ? "정서 자료 범위" : "관찰 정서"} values={result.observed_emotions}/><InfoCard icon="!" title="안전·확인 신호" values={result.risk_signals}/></div><div className="recommend-grid">{result.recommended_directions.map((item, index) => <div key={item}><b>{index + 1}. {firstSession ? "확인 순서" : "상담 방향"}</b><p>{item}</p></div>)}</div></Panel>
        <Panel><h2>{firstSession ? "첫 면담 활용 문장" : "실시간 활용 문장"}</h2><div className="phrase-grid"><div className="good"><b>✓ 사용 권장</b>{result.recommended_phrases.map(item => <p key={item}>“{item}”</p>)}</div><div className="bad"><b>× 사용 지양</b>{result.avoid_phrases.map(item => <p key={item}>“{item}”</p>)}</div><div className="tip"><b>확인 질문</b>{result.suggested_questions.map(item => <p key={item}>{item}</p>)}</div></div></Panel>
      </div>{firstSession
        ? <Panel className="report-panel"><h2>첫 회기 준비 원칙</h2><div className="report-icon">✓</div><p>상담 시작 전에는 사전문진 분석만 사용합니다. 실제 1회기 후 아래 기록 영역에서 초기상담기록지를 작성·확정합니다.</p><div className="pre-intake-rule"><b>현재 준비 항목</b><span>문진 통합 해석</span><span>안전·기능 확인 질문</span><span>이론별 탐색 가설</span><span>첫 면담 질문 후보</span></div><button className="primary" onClick={() => navigator.clipboard?.writeText(result.module_analyses.flatMap(module => [`[${module.title}]`, ...module.questions]).join("\n"))}>확인 질문 복사</button></Panel>
        : <Panel className="report-panel"><h2>이번 회기 준비 체크</h2><div className="report-icon">✓</div><p>확정된 이전 기록을 토대로 이번 회기에서 확인할 방향과 질문을 정리했습니다.</p><div className="pre-intake-rule"><b>진행 순서</b>{result.recommended_directions.slice(0, 3).map(item => <span key={item}>{item}</span>)}</div><button className="primary" onClick={() => navigator.clipboard?.writeText([...result.recommended_directions, ...result.suggested_questions].join("\n"))}>준비 내용 복사</button></Panel>}
      </div>
      <WorkflowNav step={2} onPrevious={() => moveToStep(1)} onNext={() => moveToStep(3)} nextLabel="다음: 상담자료 입력"/>
    </>
    : <Panel className="empty-analysis"><b>{preparedCase ? "2회기 분석을 실행해 주세요." : "선택한 회기의 분석을 실행해 주세요."}</b><p>{preparedCase ? "분석 실행 후 상담 방향과 문서·기록 작업 단계가 열립니다." : "1회기에는 사전문진만, 2회기부터는 직전 완료 회기까지 누적하여 상담 방향과 기록 초안을 생성합니다."}</p><WorkflowNav step={2} onPrevious={() => moveToStep(1)} nextDisabled/></Panel>)}

    {activeStep >= 3 && caseData && selectedSession && result && (preparedCase || selectedWorkflow?.status === "ready") && <RecordsWorkspace
      key={`${caseData.id}-${selectedSession.number}`}
      activeStep={activeStep}
      onStepChange={moveToStep}
      clientId={caseData.id}
      sessionNumber={selectedSession.number}
      sessionDate={preparedCase ? preparedServiceDate : selectedSession.date}
      hasNextSession={selectedSession.number < (workflow?.total_sessions ?? selectedSession.number)}
      sourceText={sessionSourceText(selectedSession)}
      goal={selectedSession.goal}
      note=""
      sourceLabel={`${caseData.case_code} · ${selectedSession.number}회기`}
      onFinalized={(nextSessionNumber) => {
        getSessionWorkflow(caseData.id).then(updated => {
          setWorkflow(updated);
          setResult(null);
          if (nextSessionNumber) setSessionNumber(nextSessionNumber);
        }).catch(() => undefined);
      }}
    />}
    {!preparedCase && selectedWorkflow?.status === "completed" && <Panel className="session-complete-notice"><b>{sessionNumber}회기 기록이 확정되었습니다.</b><p>이 회기는 열람용이며 수정 시에는 기록 변경 이력을 남기는 별도 절차가 필요합니다.</p></Panel>}
      </main>
      {caseData && selectedSession && (
        <CaseContextRail
          caseData={caseData}
          sessionNumber={sessionNumber}
          schedule={preparedCase ? formatPreparedSchedule(preparedServiceDate) : formatCaseSchedule(caseData.next_session_at, selectedSession.date)}
          goal={selectedSession.goal}
        />
      )}
    </div>
  </AppShell>;
}


const COPILOT_STEPS = ["사례 선택", "분석", "상담자료 입력", "상담기록지 작성"];


function CopilotStepper({ activeStep, maxStep, onStepChange }: { activeStep: number; maxStep: number; onStepChange: (step: number) => void }) {
  return <nav className="copilot-stepper" aria-label="상담 코파일럿 진행 단계">
    {COPILOT_STEPS.map((label, index) => {
      const step = index + 1;
      const state = step === activeStep ? "active" : step < activeStep || step < maxStep ? "complete" : "locked";
      return <button key={label} type="button" className={state} onClick={() => step <= maxStep && onStepChange(step)} disabled={step > maxStep} aria-current={step === activeStep ? "step" : undefined}>
        <span>{state === "complete" ? "✓" : step}</span><b>{label}</b>
      </button>;
    })}
  </nav>;
}


function WorkflowNav({ step, onPrevious, onNext, nextLabel = "다음 단계", nextDisabled = false }: { step: number; onPrevious?: () => void; onNext?: () => void; nextLabel?: string; nextDisabled?: boolean }) {
  return <div className="workflow-nav">
    <button type="button" onClick={onPrevious} disabled={!onPrevious}>← 이전</button>
    <span>{step} / {COPILOT_STEPS.length}</span>
    <button className="primary" type="button" onClick={onNext} disabled={!onNext || nextDisabled}>{nextLabel} →</button>
  </div>;
}


function CaseContextRail({ caseData, sessionNumber, schedule, goal }: { caseData: ClientCase; sessionNumber: number; schedule: string; goal: string }) {
  return <aside className="copilot-context-rail">
    <div className="context-rail-title"><span className="client-initial">{caseData.name.slice(0, 1)}</span><div><small>{caseData.case_code}</small><b>{caseData.name}</b></div></div>
    <dl><div><dt>준비 회기</dt><dd>{sessionNumber}회기</dd></div><div><dt>상담 일정</dt><dd>{schedule}</dd></div><div><dt>핵심 이슈</dt><dd>{caseData.primary_issue}</dd></div><div><dt>회기 목표</dt><dd>{goal}</dd></div></dl>
    <div className="context-safety-note"><b>확인 메모</b><p>{caseData.risk_notes[0] || "기록된 위험 신호 없음"}</p></div>
    <Link href={`/counselor/clients/${caseData.id}`}>사례 전체 보기 →</Link>
  </aside>;
}


function InfoCard({ icon, title, values }: { icon: string; title: string; values: string[] }) {
  return <div>{icon}<b>{title}</b>{values.map(value => <span key={value}>{value}</span>)}</div>;
}


function sessionSourceText(session: ClientCase["sessions"][number]) {
  const items = [
    ["내담자 보고", session.client_report],
    ["상담사 관찰", session.counselor_observation],
    ["상담 개입", session.interventions.join(", ")],
    ["내담자 반응", session.client_response],
    ["회기 중 변화", session.change_since_last],
    ["과제", session.homework],
    ["다음 계획", session.next_plan],
  ];
  return items.filter(([, value]) => value.trim()).map(([label, value]) => `${label}: ${value}`).join("\n");
}


function formatPreparedSchedule(value: string) {
  const date = value.replaceAll("-", ".");
  return `${date} · 09:00 ~ 09:50`;
}


function formatCaseSchedule(value: string | null | undefined, fallbackDate: string) {
  if (!value) return fallbackDate.replaceAll("-", ".");
  const start = new Date(value);
  if (Number.isNaN(start.getTime())) return fallbackDate.replaceAll("-", ".");
  const end = new Date(start.getTime() + 50 * 60 * 1000);
  const date = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(start).replaceAll("-", ".");
  const time = (item: Date) => new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false }).format(item);
  return `${date} · ${time(start)} ~ ${time(end)}`;
}
