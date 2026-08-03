"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Panel, Tag } from "@/components/UI";
import { listClients } from "@/lib/api";
import type { ClientSummary } from "@/lib/types";

export default function CounselorHome() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  useEffect(() => { listClients().then(setClients).catch(() => undefined); }, []);
  return <AppShell title="안녕하세요, 김지현 상담사님" subtitle="오늘도 따뜻한 상담으로 내담자의 변화를 함께 만들어가요.">
    <div className="counselor-home-grid">
      <div>
        <div className="welcome-banner"><div><b>오늘의 상담 일정</b><strong>3건</strong><span>첫 상담은 오전 10시에 시작합니다.</span></div><div className="house-art">⌂ ♥</div></div>
        <Panel><div className="panel-heading"><h2>내담자 목록</h2><Link href="/counselor/clients">전체 내담자 보기 →</Link></div><div className="search-box">⌕ 이름, 연락처로 검색</div><div className="client-cards">{clients.map(client => <Link href={`/counselor/clients/${client.id}`} key={client.id} className="client-card"><span className="client-icon">♟♟</span><div><b>{client.name}</b><small>{client.primary_issue}</small></div><Tag tone={client.status === "진행 중" ? "pink" : "green"}>{client.status}</Tag><strong>{client.session_count}회기</strong></Link>)}</div></Panel>
        <Link href="/training" className="training-banner"><span>◇</span><div><b>페르소나 교육</b><small>가상 내담자와 다양한 상담 상황을 연습하고 역량을 향상시켜 보세요.</small></div><strong>교육 시작하기 →</strong></Link>
      </div>
      <Panel className="schedule-panel"><div className="panel-heading"><h2>일정 관리</h2><span>2026년 8월</span></div><div className="calendar"><b>일 월 화 수 목 금 토</b><span>2　3　4　5　6　7　8</span><span>9　10　11　12　13　14　15</span><span>16　17　18　19　20　21　22</span></div><h3>2026.08.02 (일)</h3><div className="appointment"><b>10:00</b><span>박서연 · 윤지호 부부 상담</span><Tag>진행중</Tag></div><div className="appointment"><b>11:30</b><span>이수현 · 김지훈 부부 상담</span><Tag tone="gray">예정</Tag></div><div className="appointment"><b>14:00</b><span>한지은 · 정우식 부부 상담</span><Tag tone="gray">예정</Tag></div></Panel>
    </div>
  </AppShell>;
}
