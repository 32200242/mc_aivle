"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import AppShell from "@/components/AppShell";
import { Panel, Tag } from "@/components/UI";
import { getClientCase } from "@/lib/api";
import type { ClientCase } from "@/lib/types";


export default function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const [client, setClient] = useState<ClientCase | null>(null);

  useEffect(() => {
    if (params.id) getClientCase(params.id).then(setClient).catch(() => undefined);
  }, [params.id]);

  const current = client?.sessions.find(item => item.number === client.current_session_number) ?? client?.sessions.at(-1);

  return <AppShell title="내담자 관리" subtitle="접수정보·사전문진·회기별 변화를 구조화하여 확인합니다.">
    <div className="client-header"><span className="client-initial">{client?.name.slice(0, 1) ?? "-"}</span><div><h2>{client?.name ?? "불러오는 중"} <small>({client?.age ?? 0}세)</small></h2><Tag tone="green">{client?.case_code ?? "사례번호 확인 중"}</Tag></div><dl><div><dt>상담 기간</dt><dd>{client?.counseling_period ?? "-"}</dd></div><div><dt>주요 이슈</dt><dd>{client?.primary_issue ?? "-"}</dd></div><div><dt>상담 목표</dt><dd>{client?.counseling_goals[0] ?? "-"}</dd></div></dl></div>

    {client && <Panel><div className="panel-heading"><div><h2>사례 기본정보</h2><span>접수일 {client.intake_date}</span></div><Link className="primary" href="/counselor/copilot">코파일럿에서 분석하기 →</Link></div><div className="case-narrative-grid"><section><h3>가족·관계 맥락</h3><p>{client.family_composition}</p><p>{client.relationship_context}</p></section><section><h3>주호소 문제</h3><p>{client.presenting_problem}</p><p><b>의뢰 경로:</b> {client.referral_source}</p></section></div></Panel>}

    <div className="two-col"><Panel><h2>사전 문진 분석</h2>{client?.assessments.map(item => <div className="assessment-card" key={item.code}><b>{item.code} · {item.label}</b><strong>{item.score}/{item.max_score}</strong><span>{item.severity}</span><small>{item.interpretation}</small></div>)}</Panel><Panel><h2>내담자의 회기별 변화 추이</h2><div className="journey">{client?.sessions.map((session, index) => <span className="journey-item" key={session.id}><div><b>{session.number}회기</b><span>{session.change_since_last}</span></div>{index < client.sessions.length - 1 && <i>→</i>}</span>)}</div></Panel></div>

    <Panel><div className="panel-heading"><div><h2>{current?.number ?? "-"}회기 SOAP 참고정보</h2><span>코파일럿 분석 전 원기록 요약</span></div><Tag>{current?.date ?? "-"}</Tag></div><div className="soap-grid"><div className="soap s"><b>S</b><strong>Subjective</strong><p>{current?.client_report ?? "기록 없음"}</p></div><div className="soap o"><b>O</b><strong>Objective</strong><p>{current?.counselor_observation ?? "기록 없음"}</p></div><div className="soap a"><b>A</b><strong>Assessment</strong><p>{current ? `${client?.primary_issue}. ${current.client_response}` : "기록 없음"}</p></div><div className="soap p"><b>P</b><strong>Plan</strong><p>{current?.next_plan ?? "기록 없음"}</p></div></div></Panel>
  </AppShell>;
}
