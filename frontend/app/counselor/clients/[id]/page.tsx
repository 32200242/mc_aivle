"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import AppShell from "@/components/AppShell";
import AssessmentSummary from "@/components/AssessmentSummary";
import { Panel, Tag } from "@/components/UI";
import { getClientCase, getSessionWorkflow } from "@/lib/api";
import { isServiceDate, isServiceDateOrLater, serviceDateInSeoul } from "@/lib/serviceDate";
import type { ClientCase, QuestionnaireResponse, SessionWorkflow } from "@/lib/types";


const SECTION_LABELS: Record<string, string> = {
  FRPS: "가족관계 위기징후",
  FSTRESS: "가족 스트레스",
  BFI10: "성격 특성",
  DIVORCE: "관계 해체 고려",
};
type CaseHubTab = "overview" | "assessments" | "records";


export default function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const [client, setClient] = useState<ClientCase | null>(null);
  const [workflow, setWorkflow] = useState<SessionWorkflow | null>(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<CaseHubTab>("overview");

  useEffect(() => {
    if (!params.id) return;
    setError("");
    Promise.all([getClientCase(params.id), getSessionWorkflow(params.id)])
      .then(([caseData, workflowData]) => { setClient(caseData); setWorkflow(workflowData); })
      .catch(() => setError("내담자 정보를 불러오지 못했습니다."));
  }, [params.id]);

  const groupedResponses = useMemo(() => {
    const groups: Record<string, QuestionnaireResponse[]> = {};
    for (const item of client?.questionnaire_responses ?? []) (groups[item.section] ??= []).push(item);
    return groups;
  }, [client]);
  const current = client
    ? [...client.sessions]
        .filter(item => item.number <= client.session_count)
        .reverse()
        .find(item => item.official_record || item.change_since_last)
    : undefined;
  const hasUpcomingAppointment = isServiceDateOrLater(client?.next_session_at);
  const appointment = hasUpcomingAppointment && client?.next_session_at ? appointmentDetails(client.next_session_at) : null;
  const isTodayAppointment = isServiceDate(client?.next_session_at);
  const pendingRecord = workflow?.sessions.find(item => item.status === "ready");
  const pendingSession = client?.sessions.find(item => item.number === pendingRecord?.session_number);
  const recordWritingDue = Boolean(pendingRecord && pendingSession && isRecordWritingDue(pendingSession.date, client?.next_session_at));
  const scheduledSession = client?.sessions.find(session => session.number === client.session_count + 1);
  const isClosed = Boolean(client && (client.status.includes("종결") || client.counseling_period.includes("종결")));

  return <AppShell title="내담자 관리" subtitle="접수정보·사전문진·계산 점수·회기 기록을 한 사례로 연결해 확인합니다.">
    {error && <p className="dashboard-error">{error}</p>}
    <div className="client-detail-nav"><Link href="/counselor/clients">← 내담자 목록</Link></div>
    <div className="client-header"><span className="client-initial">{client?.name.slice(0, 1) ?? "-"}</span><div><h2>{client?.name ?? "불러오는 중"} <small>({client?.age ?? 0}세)</small></h2><Tag tone="green">{client?.case_code ?? "사례번호 확인 중"}</Tag></div><dl><div><dt>상담 기간</dt><dd>{client?.counseling_period ?? "-"}</dd></div><div><dt>주요 이슈</dt><dd>{client?.primary_issue ?? "-"}</dd></div><div><dt>상담 목표</dt><dd>{client?.counseling_goals[0] ?? "-"}</dd></div></dl></div>

    {recordWritingDue && pendingRecord && pendingSession && <Panel className="client-appointment-panel record-required-panel">
      <div className="client-appointment-heading"><span className="appointment-calendar-icon" aria-hidden="true">▤</span><div><small>상담 기록 작성 필요</small><h2>{pendingRecord.required_record_label}</h2><p>{formatSessionDate(pendingSession.date)} 상담 · 기록 확정 전</p></div><div className="client-appointment-actions"><Tag tone="pink">{pendingRecord.session_number}회기 미확정</Tag><Link className="primary" href={`/counselor/copilot?client=${client?.id}`}>{pendingRecord.required_record_label} 작성 →</Link></div></div>
      <dl className="client-appointment-facts"><div><dt>상담 대상</dt><dd>{pendingSession.participants.join(", ") || client?.name}</dd></div><div><dt>상담 방법</dt><dd>{pendingSession.modality || "확인 필요"}</dd></div><div><dt>회기 목표</dt><dd>{pendingSession.goal || client?.counseling_goals[0] || "기록 작성 시 확인"}</dd></div></dl>
    </Panel>}

    {!recordWritingDue && client?.next_session_at && hasUpcomingAppointment && <Panel className="client-appointment-panel">
      <div className="client-appointment-heading"><span className="appointment-calendar-icon" aria-hidden="true">◷</span><div><small>{isTodayAppointment ? "오늘 상담 일정" : "다음 상담 일정"}</small><h2>{appointment?.dateLabel ?? client.next_session_at}</h2><p>{appointment ? `${appointment.startTime} ~ ${appointment.endTime}` : "시간 확인 필요"}</p></div><div className="client-appointment-actions"><Tag tone="blue">{client.session_count + 1}회기 예정</Tag><Link className="primary" href={`/counselor/copilot?client=${client.id}`}>{client.session_count + 1}회기 상담 코파일럿 열기 →</Link></div></div>
      <dl className="client-appointment-facts"><div><dt>상담 대상</dt><dd>{scheduledSession?.participants.join(", ") || client.name}</dd></div><div><dt>상담 방법</dt><dd>{scheduledSession?.modality || "확인 예정"}</dd></div><div><dt>회기 목표</dt><dd>{scheduledSession?.goal || client.counseling_goals[0] || "상담 전 확인"}</dd></div></dl>
    </Panel>}

    <nav className="case-hub-tabs" aria-label="사례 상세 영역">
      <button type="button" className={activeTab === "overview" ? "active" : ""} onClick={() => setActiveTab("overview")}>사례 개요</button>
      <button type="button" className={activeTab === "assessments" ? "active" : ""} onClick={() => setActiveTab("assessments")}>문진·척도</button>
      <button type="button" className={activeTab === "records" ? "active" : ""} onClick={() => setActiveTab("records")}>회기 기록</button>
    </nav>

    {activeTab === "overview" && client && <>
      <Panel><div className="panel-heading"><div><h2>사례 기본정보</h2><span>접수일 {client.intake_date} · 상담 흐름을 이해하는 핵심 정보</span></div></div><div className="client-fact-grid"><div><span>성별</span><b>{client.gender}</b></div><div><span>연령</span><b>{client.age}세</b></div><div><span>직업</span><b>{client.occupation}</b></div><div><span>의뢰 경로</span><b>{client.referral_source}</b></div></div><div className="case-narrative-grid"><section><h3>가족·관계 맥락</h3><p>{client.family_composition}</p><p>{client.relationship_context}</p></section><section><h3>주호소 문제</h3><p>{client.presenting_problem}</p></section></div></Panel>
      <div className="case-overview-grid"><Panel><h2>상담 목표</h2>{client.counseling_goals.map((item, index) => <p className="overview-list-item" key={item}><span>{index + 1}</span>{item}</p>)}</Panel><Panel><h2>보호 요인</h2>{client.protective_factors.map(item => <p className="overview-list-item positive" key={item}><span>✓</span>{item}</p>)}</Panel><Panel><h2>안전·확인 메모</h2>{client.risk_notes.length ? client.risk_notes.map(item => <p className="overview-list-item caution" key={item}><span>!</span>{item}</p>) : <p>기록된 위험 신호가 없습니다.</p>}</Panel></div>
    </>}

    {activeTab === "assessments" && client && <><Panel><div className="panel-heading"><div><h2>사전문진 핵심 요약</h2><span>두드러진 응답 내용과 면담에서 확인할 지점을 먼저 보여줍니다.</span></div><Tag tone="green">4개 영역</Tag></div><AssessmentSummary assessments={client.assessments} responses={client.questionnaire_responses}/></Panel><Panel><div className="panel-heading"><div><h2>사전문진 원 응답</h2><span>총 {client.questionnaire_responses.length}문항 · 요약의 근거가 된 실제 응답을 확인합니다.</span></div><Tag tone="blue">원 응답 연결</Tag></div><div className="questionnaire-sections">{Object.entries(groupedResponses).map(([section, items]) => <details key={section} open={section === "FRPS"}><summary><span><b>{section}</b> {SECTION_LABELS[section] ?? section}</span><em>{items.length}문항</em></summary><div className="questionnaire-table-wrap"><table className="questionnaire-table"><thead><tr><th>문항</th><th>내용</th><th>응답</th></tr></thead><tbody>{items.map(item => <tr key={item.item_id}><td><b>{item.item_id}</b>{item.reverse_scored && <small>역채점</small>}</td><td>{item.text}</td><td><strong>{item.response_value}</strong><span>{item.response_label}</span></td></tr>)}</tbody></table></div></details>)}</div></Panel></>}

    {activeTab === "records" && <><Panel><div className="panel-heading"><div><h2>전체 회기 흐름</h2><span>완료 기록과 예정 회기를 시간 순서로 확인합니다.</span></div></div><div className="journey">{client?.sessions.map((session, index) => <span className="journey-item" key={session.id}><div><b>{session.number}회기</b><span>{session.official_record?.fields["상담내용"] || session.official_record?.fields["상담내용(상담개입)"] || session.change_since_last || "진행 예정"}</span></div>{index < (client?.sessions.length ?? 0) - 1 && <i>→</i>}</span>)}</div></Panel><Panel><div className="panel-heading"><div><h2>{current ? `${current.number}회기 확정 기록` : "확정된 회기 기록"}</h2><span>{current?.official_record?.record_label ?? (current ? "저장된 회기 기록" : "첫 회기 완료 후 표시됩니다.")}</span></div>{current && <Tag>{current.date}</Tag>}</div>
      {!current ? <div className="empty-analysis"><b>아직 확정된 상담 기록이 없습니다.</b><p>첫 상담을 완료하고 기록을 확정하면 이곳에 표시됩니다.</p></div> : current.official_record ? <>
        <div className="official-record-summary">{Object.entries(current.official_record.fields).map(([field, value]) => <div key={field}><b>{field}</b><p>{value}</p></div>)}</div>
        {Object.keys(current.official_record.soap).length > 0 && <><h3>SOAP 참고자료</h3><div className="soap-grid">{(["S", "O", "A", "P"] as const).map(field => <div className={`soap ${field.toLowerCase()}`} key={field}><b>{field}</b><p>{current.official_record?.soap[field] || "기록 없음"}</p></div>)}</div></>}
      </> : <div className="soap-grid"><div className="soap s"><b>S</b><strong>Subjective</strong><p>{current?.client_report || "기록 없음"}</p></div><div className="soap o"><b>O</b><strong>Objective</strong><p>{current?.counselor_observation || "기록 없음"}</p></div><div className="soap a"><b>A</b><strong>Assessment</strong><p>{current ? `${client?.primary_issue}. ${current.client_response}` : "기록 없음"}</p></div><div className="soap p"><b>P</b><strong>Plan</strong><p>{current?.next_plan || "기록 없음"}</p></div></div>}
    </Panel>{client && <ClosingReportSection client={client} isClosed={isClosed}/>}</>}
  </AppShell>;
}


function ClosingReportSection({ client, isClosed }: { client: ClientCase; isClosed: boolean }) {
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState("목표 달성에 따른 합의 종결");
  const [outcome, setOutcome] = useState("");
  const [intervention, setIntervention] = useState("");
  const [followup, setFollowup] = useState("");

  if (!isClosed) return <Panel className="closing-report-gate"><div><span className="document-type-icon closing">종결</span><div><h2>상담 종결보고서</h2><p>회기마다 작성하는 문서가 아닙니다. 사례 상태를 상담 종결로 변경한 뒤 작성할 수 있습니다.</p></div></div><button type="button" disabled>상담 종결 후 작성 가능</button></Panel>;

  return <Panel className="closing-report-panel"><div className="panel-heading"><div><h2>상담 종결보고서</h2><span>{client.name} · 총 {client.session_count}회기 상담 경과</span></div>{!editing && <button className="primary" type="button" onClick={() => setEditing(true)}>종결보고서 작성</button>}</div>
    {editing && <div className="closing-report-form"><div className="closing-report-facts"><div><span>사례번호</span><b>{client.case_code}</b></div><div><span>상담기간</span><b>{client.counseling_period}</b></div><div><span>총 회기</span><b>{client.session_count}회기</b></div></div><label>종결 사유<select value={reason} onChange={event => setReason(event.target.value)}><option>목표 달성에 따른 합의 종결</option><option>내담자 요청에 따른 종결</option><option>타 기관 연계</option><option>연락 두절·중도 종결</option><option>기타</option></select></label><label>상담목표 달성 및 주요 변화<textarea rows={5} value={outcome} onChange={event => setOutcome(event.target.value)} placeholder="초기 목표와 비교해 확인된 변화를 작성하세요."/></label><label>주요 개입과 내담자 반응<textarea rows={5} value={intervention} onChange={event => setIntervention(event.target.value)} placeholder="상담 과정에서 사용한 핵심 개입과 반응을 작성하세요."/></label><label>사후 계획·연계 및 재상담 기준<textarea rows={4} value={followup} onChange={event => setFollowup(event.target.value)} placeholder="사후 점검, 연계기관과 재상담이 필요한 조건을 작성하세요."/></label><div className="closing-report-actions"><button type="button" onClick={() => setEditing(false)}>닫기</button><button className="primary" type="button" onClick={() => downloadClosingReport(client, reason, outcome, intervention, followup)} disabled={!outcome.trim() || !intervention.trim()}>종결보고서 다운로드</button></div></div>}
  </Panel>;
}


function downloadClosingReport(client: ClientCase, reason: string, outcome: string, intervention: string, followup: string) {
  const text = [`상담 종결보고서`, `사례번호: ${client.case_code}`, `내담자: ${client.name}`, `상담기간: ${client.counseling_period}`, `총 회기: ${client.session_count}회기`, ``, `[종결 사유]`, reason, ``, `[상담목표 달성 및 주요 변화]`, outcome, ``, `[주요 개입과 내담자 반응]`, intervention, ``, `[사후 계획·연계 및 재상담 기준]`, followup].join("\n");
  const url = URL.createObjectURL(new Blob(["\ufeff", text], { type: "text/plain;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `${client.case_code}_상담종결보고서.txt`; anchor.click(); URL.revokeObjectURL(url);
}


function appointmentDetails(value: string): { dateLabel: string; startTime: string; endTime: string } | null {
  const start = new Date(value);
  if (Number.isNaN(start.getTime())) return null;
  const end = new Date(start.getTime() + 50 * 60 * 1000);
  return {
    dateLabel: new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric", weekday: "short" }).format(start),
    startTime: new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false }).format(start),
    endTime: new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false }).format(end),
  };
}


function isRecordWritingDue(sessionDate: string, appointmentAt?: string | null): boolean {
  const today = serviceDateInSeoul();
  if (sessionDate < today) return true;
  if (sessionDate > today) return false;
  if (!appointmentAt || !appointmentAt.startsWith(sessionDate)) return true;
  const start = new Date(appointmentAt);
  if (Number.isNaN(start.getTime())) return true;
  return Date.now() >= start.getTime() + 50 * 60 * 1000;
}


function formatSessionDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00+09:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric", weekday: "short" }).format(parsed);
}
