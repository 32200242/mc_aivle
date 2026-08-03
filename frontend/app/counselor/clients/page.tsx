"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Panel, Tag } from "@/components/UI";
import { listClients } from "@/lib/api";
import type { ClientSummary } from "@/lib/types";

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  useEffect(() => { listClients().then(setClients).catch(() => undefined); }, []);
  return <AppShell title="내담자 관리" subtitle="상담 이력과 변화 추이를 안전하게 관리합니다.">
    <Panel><div className="panel-heading"><h2>담당 내담자</h2><button className="primary">+ 신규 등록</button></div><div className="search-box">⌕ 이름, 연락처, 주요 이슈로 검색</div><table className="data-table"><thead><tr><th>내담자</th><th>나이</th><th>상태</th><th>주요 이슈</th><th>진행 회기</th><th>다음 상담</th><th/></tr></thead><tbody>{clients.map(client => <tr key={client.id}><td><b>{client.name}</b></td><td>{client.age}세</td><td><Tag tone={client.status === "진행 중" ? "pink" : "green"}>{client.status}</Tag></td><td>{client.primary_issue}</td><td>{client.session_count}회기</td><td>{client.next_session_at ?? "미정"}</td><td><Link href={`/counselor/clients/${client.id}`}>상세 보기 →</Link></td></tr>)}</tbody></table></Panel>
  </AppShell>;
}
