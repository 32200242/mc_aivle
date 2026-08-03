"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { MetricCard, Panel, Tag } from "@/components/UI";
import { apiFetch } from "@/lib/api";

type Summary = { center_count: number; active_clients: number; counseling_sessions: number; ai_report_minutes: number; satisfaction: number; training_completion_rate: number };

export default function AdminDashboard() {
  const [data, setData] = useState<Summary | null>(null);
  useEffect(() => { apiFetch<Summary>("/admin/dashboard").then(setData).catch(() => undefined); }, []);
  return (
    <AppShell title="통합 대시보드" subtitle="전국 가족센터의 핵심 운영 현황을 한눈에 확인합니다.">
      <div className="metric-grid four">
        <MetricCard label="전국 가족센터" value={`${data?.center_count ?? 223}개소`} note="전체 가족센터 수" tone="blue" />
        <MetricCard label="상담 이용자 수" value={(data?.active_clients ?? 158792).toLocaleString()} note="전년 대비 ▲ 6.4%" />
        <MetricCard label="상담 건수(누적)" value={(data?.counseling_sessions ?? 236101).toLocaleString()} note="전년 대비 ▲ 8.3%" tone="orange" />
        <MetricCard label="AI 상담기록 작성시간" value={`${data?.ai_report_minutes ?? 4.21}분/건`} note="전년 대비 ▼ 7.6%" tone="navy" />
      </div>
      <div className="dashboard-grid">
        <Panel className="map-panel"><div className="panel-heading"><h2>전국 가족센터 운영 현황</h2><Tag tone="blue">실시간 집계</Tag></div><div className="korea-map">대한민국<div className="map-dots">• •<br/> • • •<br/>• • • •<br/> • • •<br/> • •</div></div></Panel>
        <Panel><div className="panel-heading"><h2>우수센터</h2><span>단위: 점/100점</span></div><ol className="ranking"><li><b>1</b> 서울 강남구 가족센터 <strong>92.4</strong></li><li><b>2</b> 경기 수원시 가족센터 <strong>89.7</strong></li><li><b>3</b> 부산 해운대구 가족센터 <strong>88.3</strong></li><li><b>4</b> 인천 연수구 가족센터 <strong>87.1</strong></li><li><b>5</b> 대구 수성구 가족센터 <strong>86.0</strong></li></ol></Panel>
      </div>
      <Panel id="reports"><div className="panel-heading"><h2>핵심 운영성과</h2><span>분기별 추이</span></div><div className="mini-chart-grid"><MiniChart title="가족관계 변화" value="4.28점"/><MiniChart title="상담 만족도" value={`${data?.satisfaction ?? 4.41}점`}/><MiniChart title="교육 참여율" value={`${data?.training_completion_rate ?? 70.1}%`}/><MiniChart title="이후 서비스 개선율" value="64.9%"/></div></Panel>
    </AppShell>
  );
}

function MiniChart({ title, value }: { title: string; value: string }) {
  return <div className="mini-chart"><span>{title}</span><strong>{value}</strong><svg viewBox="0 0 220 65"><polyline points="4,54 42,44 80,47 118,30 156,34 216,15" fill="none" stroke="currentColor" strokeWidth="4"/><line x1="0" y1="60" x2="220" y2="60" stroke="#e9e9ee"/></svg></div>;
}
