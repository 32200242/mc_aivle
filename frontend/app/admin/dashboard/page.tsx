"use client";

import { type KeyboardEvent, type PointerEvent as ReactPointerEvent, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { MetricCard, Panel, Tag } from "@/components/UI";
import { SOUTH_KOREA_SGIS_MAP } from "@/data/southKoreaSgis";
import { apiFetch } from "@/lib/api";
import type { DashboardCenter, DashboardRegion, DashboardSummary } from "@/lib/types";

const PERIODS = [90, 180, 365] as const;
const ADMIN_TIME_BASELINE_MINUTES = 11.7;
const KOREA_MAP = SOUTH_KOREA_SGIS_MAP;

export default function AdminDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [centerId, setCenterId] = useState<string | null>(null);
  const [days, setDays] = useState<(typeof PERIODS)[number]>(90);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ days: String(days) });
    if (regionId) params.set("region_id", regionId);
    if (centerId) params.set("center_id", centerId);
    setLoading(true);
    setError("");
    apiFetch<DashboardSummary>(`/admin/dashboard?${params.toString()}`)
      .then(setData)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [regionId, centerId, days]);

  const selectedRegion = data?.regions.find((region) => region.id === regionId) ?? null;
  const selectedCenter = data?.centers.find((center) => center.id === centerId) ?? null;
  const administrativeTimeReduction = data
    ? Math.max(0, Math.round((1 - data.ai_report_minutes / ADMIN_TIME_BASELINE_MINUTES) * 100))
    : 0;

  function selectRegion(region: DashboardRegion) {
    setRegionId(region.id);
    setCenterId(null);
  }

  function selectCenter(center: DashboardCenter) {
    setRegionId(center.region_id);
    setCenterId(center.id);
  }

  return (
    <AppShell title="통합 대시보드" subtitle="지역·센터·내담자군별 월간 운영 흐름을 연결해 확인합니다." referenceDate={data?.data_as_of}>
      <div className="dashboard-toolbar">
        <div className="scope-breadcrumb">
          <button className={!regionId ? "active" : ""} onClick={() => { setRegionId(null); setCenterId(null); }}>전국</button>
          {selectedRegion && <><span>›</span><button className={!centerId ? "active" : ""} onClick={() => setCenterId(null)}>{selectedRegion.short_name}</button></>}
          {selectedCenter && <><span>›</span><b>{selectedCenter.name}</b></>}
        </div>
        <div className="period-switch" aria-label="조회 기간">
          {PERIODS.map((period) => <button key={period} className={days === period ? "active" : ""} onClick={() => setDays(period)}>{period === 365 ? "1년" : period === 180 ? "6개월" : "3개월"}</button>)}
        </div>
      </div>

      {error && <p className="dashboard-error">{error}</p>}
      {loading && !data ? <Panel><p className="dashboard-loading">운영 데이터를 집계하고 있습니다.</p></Panel> : data && <>
        <div className="metric-grid dashboard-kpis">
          <MetricCard label="기관" value={`${data.center_count.toLocaleString()}개소`} note={`${data.scope.label} 조회 범위`} tone="blue" />
          <MetricCard label="상담인력" value={`${data.counselor_count.toLocaleString()}명`} note={`교육 이수 ${data.training_completion_rate}%`} />
          <MetricCard label="누적 상담 참여인원" value={`${data.counseling_sessions.toLocaleString()}명`} note={`${formatChange(data.changes.sessions)} · ${data.period_days}일`} tone="navy" />
          <MetricCard label="행정 업무 시간" value={`${data.ai_report_minutes.toFixed(1)}분/건`} note={`이전 대비 ${administrativeTimeReduction}% 감소`} tone="orange" />
          <MetricCard label="상담 만족도" value={`${data.satisfaction.toFixed(2)}점`} note={`사전·사후 완료 ${data.pre_post_completion_rate}%`} tone="blue" />
        </div>

        <div className="dashboard-map-grid">
          <Panel className="regional-map-panel">
            <div className="panel-heading"><div><h2>지역별 운영 현황</h2><small>지역을 선택하면 센터 목록과 지표가 함께 바뀝니다.</small></div><Tag tone="blue">{data.period_start}~{data.data_as_of}</Tag></div>
            <KoreaRegionMap regions={data.regions} onSelect={selectRegion} />
            <div className="map-legend"><span><i className="low"/>참여인원 적음</span><span><i className="high"/>참여인원 많음</span></div>
          </Panel>

          <Panel className="center-browser-panel">
            <div className="panel-heading"><div><h2>{regionId ? `${selectedRegion?.name ?? "지역"} 센터` : "우수 센터"}</h2><small>{data.centers.length}개 기관 · 행을 눌러 상세 확인</small></div>{centerId && <button className="compact-button" onClick={() => setCenterId(null)}>센터 선택 해제</button>}</div>
            <div className="center-browser-list">
              {data.centers.slice(0, regionId ? data.centers.length : 18).map((center) => (
                <button key={center.id} className={center.selected ? "selected" : ""} onClick={() => selectCenter(center)}>
                  <span><b>{center.name}</b><small>{center.center_type}</small></span>
                  <span><b>{center.sessions.toLocaleString()}명</b><small>상담 {center.counselor_count}명 · 사례 {center.active_clients}명</small></span>
                  <span><b>{center.satisfaction.toFixed(2)}</b><small>대기 {center.waitlist}명</small></span>
                </button>
              ))}
            </div>
          </Panel>
        </div>

        <div className="dashboard-detail-grid">
          <Panel>
            <div className="panel-heading"><div><h2>월별 누적 상담 참여인원 추이</h2><small>{data.scope.label} · 조회기간의 일별 참여인원을 월별 연인원으로 집계</small></div><Tag tone={data.changes.sessions >= 0 ? "green" : "orange"}>{formatChange(data.changes.sessions)}</Tag></div>
            <SessionTrend data={data.trend} target={data.service_targets.scope_monthly_contact_target} />
          </Panel>
          <Panel>
            <div className="panel-heading"><div><h2>내담자 주요 호소영역</h2><small>현재 상담사 배정 사례 기준</small></div><Tag tone="purple">총 {data.active_clients.toLocaleString()}명</Tag></div>
            <div className="issue-bars">
              {data.issues.map((issue) => <div key={issue.issue}><span>{issue.issue}</span><div><i style={{ width: `${data.active_clients ? issue.client_count / data.active_clients * 100 : 0}%` }}/></div><b>{issue.client_count.toLocaleString()}</b><small>집중검토 {issue.priority_review_count}</small></div>)}
            </div>
          </Panel>
        </div>

      </>}
    </AppShell>
  );
}

function KoreaRegionMap({ regions, onSelect }: { regions: DashboardRegion[]; onSelect: (region: DashboardRegion) => void }) {
  const maximum = Math.max(...regions.map((region) => region.sessions), 1);
  const byId = new Map(regions.map(region => [region.id, region]));
  const selectByKeyboard = (event: KeyboardEvent<SVGGElement>, region: DashboardRegion) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(region);
    }
  };

  return <div className="korea-region-map" role="group" aria-label="대한민국 지도에서 17개 시도 선택">
    <svg className="korea-map-shape" viewBox={KOREA_MAP.viewBox} preserveAspectRatio="xMidYMid meet" aria-label="대한민국 17개 시도별 상담 운영 현황">
      {KOREA_MAP.locations.map(location => {
        const region = byId.get(location.id);
        if (!region) return null;
        const strength = .18 + region.sessions / maximum * .82;
        return <g
          key={location.id}
          className={`korea-province ${region.selected ? "selected" : ""}`}
          role="button"
          tabIndex={0}
          aria-label={`${region.name}, 기관 ${region.center_count}개, 누적 상담 참여인원 ${region.sessions.toLocaleString()}명`}
          aria-pressed={region.selected}
          onClick={() => onSelect(region)}
          onKeyDown={event => selectByKeyboard(event, region)}
        >
          <path d={location.path} style={{ fill: `hsl(214 72% ${Math.round(94 - strength * 43)}%)` }}>
            <title>{region.name}: 기관 {region.center_count}개, 누적 상담 참여인원 ${region.sessions.toLocaleString()}명</title>
          </path>
        </g>;
      })}
      {KOREA_MAP.locations.map(location => {
        const region = byId.get(location.id);
        if (!region) return null;
        const point = location.label;
        return <g
          key={`label-${region.id}`}
          className={`korea-map-label ${region.selected ? "selected" : ""}`}
          role="button"
          tabIndex={0}
          aria-label={`${region.name} 선택`}
          onClick={() => onSelect(region)}
          onKeyDown={event => selectByKeyboard(event, region)}
          transform={`translate(${point.x} ${point.y})`}
        >
          <rect x="-22" y="-14" width="44" height="28" rx="7" />
          <text className="region-name" textAnchor="middle" y="-1">{region.short_name}</text>
          <text className="region-value" textAnchor="middle" y="10">{region.sessions.toLocaleString()}</text>
        </g>;
      })}
    </svg>
  </div>;
}

function SessionTrend({ data, target }: { data: DashboardSummary["trend"]; target: number }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const monthly = useMemo(() => aggregateMonthlySessions(data), [data]);
  const geometry = useMemo(() => {
    if (!monthly.length) return { path: "", points: [] as Array<{ x: number; y: number }>, ticks: [] as Array<{ value: number; y: number }>, targetY: 170 };
    const maxValue = Math.max(...monthly.map((item) => item.sessions), target, 1);
    const step = niceStep(maxValue / 4);
    const max = step * 4;
    const denominator = Math.max(1, monthly.length - 1);
    const width = 1000;
    const points = monthly.map((item, index) => ({
      x: index / denominator * width,
      y: 170 - item.sessions / max * 140,
    }));
    const ticks = Array.from({ length: 5 }, (_, index) => ({ value: index * step, y: 170 - index * step / max * 140 }));
    return { path: points.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" "), points, ticks, targetY: 170 - target / max * 140 };
  }, [monthly, target]);
  const total = monthly.reduce((sum, item) => sum + item.sessions, 0);
  const hovered = hoveredIndex === null ? null : monthly[hoveredIndex];
  const hoveredPoint = hoveredIndex === null ? null : geometry.points[hoveredIndex];

  function updateHover(event: ReactPointerEvent<SVGRectElement>) {
    if (!monthly.length) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(1000, (event.clientX - bounds.left) / bounds.width * 1000));
    const index = Math.round(x / 1000 * Math.max(0, monthly.length - 1));
    setHoveredIndex(index);
  }

  return (
    <div className="session-trend">
      <div className="session-trend-summary">
        <span>기간 누적</span>
        <strong>{total.toLocaleString()}명</strong>
        <span className="service-target-key"><i />월 목표 {Math.round(target).toLocaleString()}명</span>
      </div>
      <div className="session-trend-chart">
        <div className="session-trend-graph">
          <div className="session-trend-y-axis" aria-hidden="true">
            <span className="chart-unit">명/월</span>
            {geometry.ticks.map(tick => (
              <span
                key={tick.value}
                className="chart-y-label"
                style={{ top: `${tick.y / 190 * 100}%` }}
              >
                {Math.round(tick.value).toLocaleString()}
              </span>
            ))}
          </div>
          <div className="session-trend-plot">
            <svg viewBox="0 0 1000 190" preserveAspectRatio="none" aria-label="월별 누적 상담 참여인원 추이">
              <title>월별 누적 상담 참여인원 추이</title>
              <desc>그래프 위에 마우스를 올리면 해당 월의 참여인원과 월 목표를 확인할 수 있습니다.</desc>
              {geometry.ticks.map(tick => <line key={tick.value} x1="0" y1={tick.y} x2="1000" y2={tick.y}/>)}
              <line x1="0" y1={geometry.targetY} x2="1000" y2={geometry.targetY} className="service-target-line"/>
              <polyline points={geometry.path} fill="none" stroke="currentColor" strokeWidth="4" vectorEffect="non-scaling-stroke"/>
              {hoveredPoint && <>
                <line x1={hoveredPoint.x} y1="30" x2={hoveredPoint.x} y2="170" className="chart-hover-guide"/>
                <circle cx={hoveredPoint.x} cy={hoveredPoint.y} r="6" className="chart-hover-marker" vectorEffect="non-scaling-stroke"/>
              </>}
              <rect x="0" y="20" width="1000" height="155" className="chart-hover-hit" onPointerMove={updateHover} onPointerLeave={() => setHoveredIndex(null)}/>
            </svg>
            {hovered && hoveredPoint && <div
              className={`chart-hover-tooltip ${hoveredPoint.x > 840 ? "align-right" : hoveredPoint.x < 160 ? "align-left" : ""}`}
              role="tooltip"
              style={{ left: `${hoveredPoint.x / 10}%`, top: `${hoveredPoint.y / 1.9}%` }}
            >
              <b>{formatMonth(hovered.month)}</b>
              <span>참여인원 {hovered.sessions.toLocaleString()}명</span>
              <small>월 목표 {Math.round(target).toLocaleString()}명</small>
            </div>}
          </div>
        </div>
        <div className="trend-axis">
          <span>{monthly[0]?.month}</span>
          <span>{monthly.at(-1)?.month}</span>
        </div>
      </div>
    </div>
  );
}

function aggregateMonthlySessions(data: DashboardSummary["trend"]) {
  const grouped = new Map<string, number>();
  data.forEach(item => {
    const month = item.date.slice(0, 7);
    grouped.set(month, (grouped.get(month) ?? 0) + item.sessions);
  });
  return Array.from(grouped, ([month, sessions]) => ({ month, sessions }));
}

function niceStep(value: number) {
  const power = 10 ** Math.floor(Math.log10(Math.max(value, 1)));
  const normalized = value / power;
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return factor * power;
}

function formatMonth(value: string) {
  const [year, month] = value.split("-");
  return `${year}년 ${Number(month)}월`;
}

function formatChange(value: number) {
  if (!value) return "변동 없음";
  return `${value > 0 ? "▲" : "▼"} ${Math.abs(value).toFixed(1)}%`;
}
