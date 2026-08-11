"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Panel, Tag } from "@/components/UI";
import { listClientsPage } from "@/lib/api";
import type { ClientPage } from "@/lib/types";


const EMPTY_PAGE: ClientPage = { items: [], total: 0, page: 1, page_size: 10, pages: 1 };


export default function ClientsPage() {
  const [result, setResult] = useState<ClientPage>(EMPTY_PAGE);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    listClientsPage(page, 10, query)
      .then(data => { if (active) setResult(data); })
      .catch(() => { if (active) setError("내담자 목록을 불러오지 못했습니다."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, query]);

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    setPage(1);
    setQuery(draft.trim());
  };

  return <AppShell title="내담자 관리" subtitle="내담자 정보와 상담 이력을 확인합니다.">
    <Panel>
      <div className="panel-heading clients-heading">
        <div><h2>내담자 목록</h2><span>총 {result.total.toLocaleString()}명 · 페이지당 10명</span></div>
      </div>
      <form className="client-search" onSubmit={submitSearch}>
        <input value={draft} onChange={event => setDraft(event.target.value)} placeholder="이름, 사례번호, 주요 이슈로 검색" aria-label="내담자 검색" />
        <button className="primary" type="submit">검색</button>
        {(query || draft) && <button type="button" onClick={() => { setDraft(""); setQuery(""); setPage(1); }}>초기화</button>}
      </form>
      {error && <p className="dashboard-error">{error}</p>}
      {loading ? <p className="client-list-state">내담자를 불러오는 중입니다.</p> : result.items.length === 0 ? <p className="client-list-state">검색 조건에 맞는 내담자가 없습니다.</p> : <div className="client-table-wrap">
        <table className="data-table"><thead><tr><th>내담자</th><th>나이</th><th>상태</th><th>주요 이슈</th><th>완료 회기</th><th>다음 상담</th><th/></tr></thead><tbody>{result.items.map(client => <tr key={client.id}><td><b>{client.name}</b><small>{client.case_code}</small></td><td>{client.age}세</td><td><Tag tone={client.status.includes("준비") || client.status === "상담 시작 전" ? "pink" : "green"}>{client.status}</Tag></td><td>{client.primary_issue}</td><td>{client.session_count}회기</td><td>{formatAppointment(client.next_session_at)}</td><td><Link href={`/counselor/clients/${client.id}`}>상세 보기 →</Link></td></tr>)}</tbody></table>
      </div>}
      <div className="client-pagination" aria-label="내담자 목록 페이지 이동">
        <button disabled={loading || result.page <= 1} onClick={() => setPage(current => Math.max(1, current - 1))}>← 이전</button>
        <span><b>{result.page}</b> / {result.pages}</span>
        <button disabled={loading || result.page >= result.pages} onClick={() => setPage(current => Math.min(result.pages, current + 1))}>다음 →</button>
      </div>
    </Panel>
  </AppShell>;
}


function formatAppointment(value?: string | null): string {
  if (!value) return "미정";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  if (parsed.getTime() < Date.now()) return "상담기록지 작성 필요";
  return new Intl.DateTimeFormat("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(parsed);
}
