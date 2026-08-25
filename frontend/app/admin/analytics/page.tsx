"use client";

import { type PointerEvent as ReactPointerEvent, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { MetricCard, Panel, Tag } from "@/components/UI";
import { apiFetch } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

export default function AnalyticsPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [regionId, setRegionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ days: "365" });
    if (regionId) params.set("region_id", regionId);
    setLoading(true);
    setError("");
    apiFetch<DashboardSummary>(`/admin/dashboard?${params.toString()}`)
      .then(setData)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [regionId]);

  const currentSessions = data?.trend.reduce((sum, row) => sum + row.sessions, 0) ?? 0;
  const forecastSessions = data?.forecast.reduce((sum, row) => sum + row.predicted_sessions, 0) ?? 0;
  const dailyAverage = data?.trend.length ? currentSessions / data.trend.length : 0;
  const forecastDailyAverage = data?.forecast.length ? forecastSessions / data.forecast.length : 0;
  const forecastChange = dailyAverage ? (forecastDailyAverage / dailyAverage - 1) * 100 : 0;
  const peakForecast = useMemo(() => {
    if (!data?.forecast.length) return null;
    return data.forecast.reduce((peak, row) => row.predicted_sessions > peak.predicted_sessions ? row : peak);
  }, [data]);
  const peakDate = peakForecast
    ? new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", weekday: "short" }).format(new Date(`${peakForecast.date}T00:00:00`))
    : "-";
  const recommendation = data ? operatingRecommendation(data, forecastChange) : "";
  const improvementPriorities = useMemo(
    () => data ? buildImprovementPriorities(data, forecastChange) : [],
    [data, forecastChange],
  );

  return (
    <AppShell title="상담 수요 전망" subtitle="최근 상담 실적과 향후 28일 수요를 바탕으로 인력과 예약 운영을 검토합니다." referenceDate={data?.data_as_of}>
      <div className="analytics-toolbar">
        <label>
          조회 지역
          <select value={regionId} onChange={(event) => setRegionId(event.target.value)} disabled={!data}>
            <option value="">전국</option>
            {data?.regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}
          </select>
        </label>
        <span>{loading ? "운영 전망 계산 중…" : `${data?.data_as_of ?? "-"} 기준`}</span>
      </div>

      {error && <p className="dashboard-error">{error}</p>}
      {loading && !data && <Panel><p className="dashboard-loading">저장된 운영 데이터를 불러오고 있습니다.</p></Panel>}
      {data && <>
        <div className="metric-grid dashboard-kpis">
          <MetricCard label="조회 범위" value={data.scope.label} note={`${data.center_count}개 기관`} tone="blue" />
          <MetricCard label="최근 일평균 참여인원" value={`${Math.round(dailyAverage).toLocaleString()}명`} note="최근 365일" />
          <MetricCard label="향후 28일 누적 참여인원" value={`${Math.round(forecastSessions).toLocaleString()}명`} note={`일평균 ${Math.round(forecastDailyAverage).toLocaleString()}명`} tone="navy" />
          <MetricCard label="예상 변화" value={`${forecastChange >= 0 ? "+" : ""}${forecastChange.toFixed(1)}%`} note="최근 일평균 대비" tone={forecastChange >= 0 ? "orange" : "blue"} />
        </div>

        <Panel>
          <div className="panel-heading">
            <div><h2>월별 상담 참여인원 추이와 28일 전망</h2><small>완료된 월의 누적 상담 참여인원과 향후 28일 전망을 비교하며, 초록 점선은 2026년 공식 목표의 월평균입니다.</small></div>
            <Tag tone="purple">운영 전망 · 28일</Tag>
          </div>
          <ForecastChart data={data} />
          <div className="chart-target-note"><b>2026 목표 참고</b><span>가족상담 서비스 이용자 {data.service_targets.family_counseling_users.toLocaleString()}명 · 이용자 만족도 {data.service_targets.family_counseling_satisfaction.toFixed(1)}점</span><small>{data.service_targets.interpretation}</small></div>
        </Panel>

        <div className="analytics-grid">
          <Panel>
            <div className="panel-heading"><div><h2>수요 전망 요약</h2><small>센터 운영계획 수립에 필요한 핵심 수치만 표시합니다.</small></div><Tag tone={forecastChange >= 0 ? "orange" : "blue"}>{forecastChange >= 0 ? "수요 증가" : "수요 감소"}</Tag></div>
            <dl className="forecast-summary">
              <div><dt>28일 누적 상담 참여인원</dt><dd>{Math.round(forecastSessions).toLocaleString()}명</dd></div>
              <div><dt>예상 일평균 참여인원</dt><dd>{Math.round(forecastDailyAverage).toLocaleString()}명</dd></div>
              <div><dt>최대 수요 예상일</dt><dd>{peakDate}</dd><small>{peakForecast ? `${Math.round(peakForecast.predicted_sessions).toLocaleString()}명 예상` : "-"}</small></div>
              <div><dt>최근 대비</dt><dd>{forecastChange >= 0 ? "+" : ""}{forecastChange.toFixed(1)}%</dd></div>
            </dl>
            <div className="operations-recommendation"><b>운영 제안</b><p>{recommendation}</p></div>
          </Panel>

          <Panel>
            <div className="panel-heading"><div><h2>운영 검토 지표</h2><small>예측은 인력·예약 운영 검토용이며 개인의 임상 위험도를 예측하지 않습니다.</small></div></div>
            <dl className="forecast-facts">
              <div><dt>현재 대기 인원</dt><dd>{data.waitlist_count.toLocaleString()}명</dd></div>
              <div><dt>예상 상담 수용률</dt><dd>{data.queue.forecast_utilization_rate.toFixed(1)}%</dd></div>
              <div><dt>예약 대기압력</dt><dd>{data.queue.pressure_level}</dd></div>
              <div><dt>예상 대기 인원</dt><dd>{data.queue.expected_queue_sessions.toLocaleString()}명</dd></div>
              <div><dt>기존 대기 소진</dt><dd>{data.queue.backlog_clearance_days === null ? "현재 용량으로 불가" : `${data.queue.backlog_clearance_days.toFixed(1)}일`}</dd></div>
              <div><dt>권장 추가 일일 슬롯</dt><dd>{data.queue.recommended_additional_daily_slots.toLocaleString()}건</dd></div>
              <div><dt>상담 만족도</dt><dd>{data.satisfaction.toFixed(2)} / 5</dd></div>
              <div><dt>전망 기간</dt><dd>{data.forecast[0]?.date}~{data.forecast.at(-1)?.date}</dd></div>
            </dl>
          </Panel>
        </div>

        <ImprovementPriorityPanel priorities={improvementPriorities} scopeLabel={data.scope.label} />
      </>}
    </AppShell>
  );
}

type ImprovementPriority = {
  key: string;
  label: string;
  description: string;
  importance: number;
  expectedEffect: number;
};

function ImprovementPriorityPanel({ priorities, scopeLabel }: { priorities: ImprovementPriority[]; scopeLabel: string }) {
  return <Panel className="improvement-priority-panel">
    <div className="panel-heading">
      <div>
        <h2>개선 우선순위 TOP 5</h2>
        <small>{scopeLabel} · 운영 실적과 수요 전망을 함께 반영한 개선 시나리오</small>
      </div>
      <Tag tone="pink">운영 예측</Tag>
    </div>
    <div className="improvement-priority-head" aria-hidden="true">
      <span>우선순위</span><span>개선 영역</span><span>중요도(%)</span><span>개선 시 예상 효과</span>
    </div>
    <ol className="improvement-priority-list">
      {priorities.map((priority, index) => <li key={priority.key}>
        <span className="priority-rank">{index + 1}</span>
        <div className="priority-name"><b>{priority.label}</b><small>{priority.description}</small></div>
        <strong className="priority-importance">{priority.importance.toFixed(1)}%</strong>
        <div className="priority-effect">
          <div aria-label={`${priority.label} 중요도 ${priority.importance.toFixed(1)}%`}><i style={{ width: `${priority.importance / Math.max(priorities[0]?.importance ?? 1, 1) * 100}%` }} /></div>
          <b>+{priority.expectedEffect.toFixed(1)}점</b>
        </div>
      </li>)}
    </ol>
    <p className="improvement-priority-note">예상 효과는 상위 개선 영역을 우선 적용하는 시나리오에서 통합 운영 성과지수의 상승폭을 추정한 값입니다.</p>
  </Panel>;
}

function buildImprovementPriorities(data: DashboardSummary, forecastChange: number): ImprovementPriority[] {
  const activeClients = Math.max(data.active_clients, 1);
  const priorityReviewRate = data.issues.reduce((sum, issue) => sum + issue.priority_review_count, 0) / activeClients;
  const waitRate = data.waitlist_count / activeClients;
  const utilizationPressure = Math.max(0, data.queue.forecast_utilization_rate - 80);
  const pressureBonus = data.queue.pressure_level === "높음" ? 12 : data.queue.pressure_level === "보통" ? 6 : 0;
  const candidates = [
    {
      key: "institution-operations",
      label: "기관 운영관리",
      description: "업무 처리시간과 상담 수용 여력",
      raw: 22 + Math.min(20, data.ai_report_minutes * 1.6) + utilizationPressure * .25,
    },
    {
      key: "counseling-service",
      label: "상담서비스 운영",
      description: "수요 변화와 집중검토 사례 대응",
      raw: 20 + Math.min(16, Math.abs(forecastChange) * .55) + Math.min(15, priorityReviewRate * 100),
    },
    {
      key: "staff-development",
      label: "종사자 전문성 강화",
      description: "교육 미이수 보완과 상담 품질 유지",
      raw: 15 + Math.max(0, 100 - data.training_completion_rate) * .45,
    },
    {
      key: "wait-and-booking",
      label: "대기·예약 관리",
      description: "기존 대기 해소와 추가 상담 슬롯 배치",
      raw: 18 + Math.min(25, waitRate * 100) + pressureBonus,
    },
    {
      key: "user-satisfaction",
      label: "이용자 만족도",
      description: "상담 경험과 사전·사후 응답 관리",
      raw: 12 + Math.max(0, 4.5 - data.satisfaction) * 18 + Math.max(0, 80 - data.pre_post_completion_rate) * .2,
    },
  ];
  const total = candidates.reduce((sum, item) => sum + item.raw, 0) || 1;

  return candidates
    .map(item => {
      const importance = item.raw / total * 100;
      return {
        key: item.key,
        label: item.label,
        description: item.description,
        importance,
        expectedEffect: Math.min(9.9, 1.5 + importance * .23),
      };
    })
    .sort((left, right) => right.importance - left.importance);
}

function ForecastChart({ data }: { data: DashboardSummary }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const history = useMemo(() => aggregateCompletedMonths(data.trend, data.data_as_of).slice(-12), [data.trend, data.data_as_of]);
  const forecast = data.forecast;
  const geometry = useMemo(() => {
    const target = data.service_targets.scope_monthly_contact_target;
    const forecastTotal = forecast.reduce((sum, row) => sum + row.predicted_sessions, 0);
    const forecastLower = forecast.reduce((sum, row) => sum + row.lower, 0);
    const forecastUpper = forecast.reduce((sum, row) => sum + row.upper, 0);
    const allValues = [...history.map((row) => row.sessions), forecastLower, forecastUpper, target];
    const maxValue = Math.max(...allValues, 1);
    const step = niceStep(maxValue / 4);
    const max = step * 4;
    const historyDivisor = Math.max(history.length - 1, 1);
    const left = 58;
    const right = 890;
    const historyEndX = 710;
    const forecastX = right;
    const y = (value: number) => 240 - value / max * 205;
    const historyX = (index: number) => left + index / historyDivisor * (historyEndX - left);
    const historyPlot = history.map((row, index) => ({
      x: historyX(index),
      y: y(row.sessions),
      label: formatMonth(row.month),
      value: row.sessions,
      kind: "history" as const,
    }));
    const forecastPoint = {
      x: forecastX,
      y: y(forecastTotal),
      label: forecast.length ? `${formatDate(forecast[0].date)}~${formatDate(forecast.at(-1)?.date ?? forecast[0].date)}` : "향후 28일",
      value: forecastTotal,
      lower: forecastLower,
      upper: forecastUpper,
      kind: "forecast" as const,
    };
    const historyPoints = historyPlot.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
    const predicted = `${historyEndX},${y(history.at(-1)?.sessions ?? forecastTotal).toFixed(1)} ${forecastX},${y(forecastTotal).toFixed(1)}`;
    const yTicks = Array.from({ length: 5 }, (_, index) => ({ value: index * step, y: 240 - index * step / max * 205 }));
    return { historyPoints, historyPlot, forecastPoint, hoverPoints: [...historyPlot, forecastPoint], predicted, splitX: historyEndX, forecastX, forecastLowerY: y(forecastLower), forecastUpperY: y(forecastUpper), yTicks, targetY: y(target), target };
  }, [history, forecast, data.service_targets.scope_monthly_contact_target]);

  const hovered = hoveredIndex === null ? null : geometry.hoverPoints[hoveredIndex];

  function updateHover(event: ReactPointerEvent<SVGRectElement>) {
    if (!geometry.hoverPoints.length) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = Math.max(58, Math.min(890, (event.clientX - bounds.left) / bounds.width * 900));
    let nearest = 0;
    geometry.hoverPoints.forEach((point, index) => {
      if (Math.abs(point.x - x) < Math.abs(geometry.hoverPoints[nearest].x - x)) nearest = index;
    });
    setHoveredIndex(nearest);
  }

  return <div className="forecast-chart">
    <svg viewBox="0 0 900 260" preserveAspectRatio="xMidYMid meet" aria-label="월별 누적 상담 참여인원과 28일 참여인원 전망">
      <title>월별 누적 상담 참여인원과 향후 28일 전망</title>
      <desc>마우스를 올리면 월별 실적 또는 전망 기간의 예측값과 예측 범위를 확인할 수 있습니다.</desc>
      {geometry.yTicks.map(tick => <g key={tick.value}><line x1="58" y1={tick.y} x2="900" y2={tick.y}/><text x="50" y={tick.y + 4} textAnchor="end" className="chart-y-label">{Math.round(tick.value).toLocaleString()}</text></g>)}
      <text x="4" y="14" className="chart-unit">단위: 명/월</text>
      <polyline points={geometry.historyPoints} className="history-line" />
      <polyline points={geometry.predicted} className="forecast-line" />
      <line x1={geometry.forecastX} y1={geometry.forecastUpperY} x2={geometry.forecastX} y2={geometry.forecastLowerY} className="forecast-range-line" />
      <line x1={geometry.forecastX - 7} y1={geometry.forecastUpperY} x2={geometry.forecastX + 7} y2={geometry.forecastUpperY} className="forecast-range-line" />
      <line x1={geometry.forecastX - 7} y1={geometry.forecastLowerY} x2={geometry.forecastX + 7} y2={geometry.forecastLowerY} className="forecast-range-line" />
      <line x1="58" y1={geometry.targetY} x2="900" y2={geometry.targetY} className="service-target-line" />
      <g className="service-target-legend" transform="translate(63 11)">
        <line x1="0" y1="0" x2="25" y2="0" className="service-target-line" />
        <text x="32" y="3" className="service-target-label">2026 월평균 목표 {Math.round(geometry.target).toLocaleString()}명</text>
      </g>
      <line x1={geometry.splitX} y1="15" x2={geometry.splitX} y2="245" className="forecast-split" />
      {geometry.historyPlot.map(point => <circle key={point.label} cx={point.x} cy={point.y} r="3.5" className="history-point"/>)}
      <circle cx={geometry.forecastPoint.x} cy={geometry.forecastPoint.y} r="5" className="forecast-point"/>
      {hovered && <>
        <line x1={hovered.x} y1="15" x2={hovered.x} y2="245" className="chart-hover-guide"/>
        <circle cx={hovered.x} cy={hovered.y} r="6" className={`chart-hover-marker ${hovered.kind}`}/>
      </>}
      <rect x="58" y="15" width="832" height="230" className="chart-hover-hit" onPointerMove={updateHover} onPointerLeave={() => setHoveredIndex(null)}/>
    </svg>
    {hovered && <div
      className={`chart-hover-tooltip ${hovered.x > 800 ? "align-right" : hovered.x < 145 ? "align-left" : ""}`}
      role="tooltip"
      style={{ left: `${hovered.x / 9}%`, top: `${hovered.y / 2.6}%` }}
    >
      <b>{hovered.label}</b>
      <span>{hovered.kind === "forecast" ? "예상 참여인원" : "참여인원"} {Math.round(hovered.value).toLocaleString()}명</span>
      {hovered.kind === "forecast" && <small>예측 범위 {Math.round(hovered.lower).toLocaleString()}~{Math.round(hovered.upper).toLocaleString()}명</small>}
      {hovered.kind === "history" && <small>월별 누적 실적</small>}
    </div>}
    <div className="forecast-axis"><span>{history[0]?.month}</span><span style={{ left: `${geometry.splitX / 9}%` }}>전망 시작</span><span>향후 28일</span></div>
  </div>;
}

function aggregateCompletedMonths(data: DashboardSummary["trend"], asOf: string) {
  const currentMonth = asOf.slice(0, 7);
  const grouped = new Map<string, number>();
  data.forEach(item => {
    const month = item.date.slice(0, 7);
    if (month === currentMonth) return;
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

function formatDate(value: string) {
  const [, month, day] = value.split("-");
  return `${Number(month)}월 ${Number(day)}일`;
}

function operatingRecommendation(data: DashboardSummary, forecastChange: number) {
  if (data.queue.pressure_level === "높음") {
    return "대기 인원이 많고 상담 수용률이 높은 상태입니다. 수요가 집중되는 요일의 예약 슬롯과 대체 상담인력 배정을 우선 검토하세요.";
  }
  if (data.queue.pressure_level === "주의") {
    return `현재 인력 기준으로 일일 ${data.queue.recommended_additional_daily_slots}개 슬롯 확보를 검토하고, 주간 대기 인원 변화를 함께 확인하세요.`;
  }
  if (forecastChange >= 5) {
    return "상담 수요 증가가 예상됩니다. 기존 인력의 가용시간을 확인하고 초기상담 예약 여유분을 확보하세요.";
  }
  if (forecastChange <= -5) {
    return "수요가 다소 완화될 전망입니다. 대기 사례 재연락과 사후점검 일정을 배치해 가용시간을 활용하세요.";
  }
  return "현재 수준과 비슷한 수요가 예상됩니다. 현행 배정을 유지하되 주간 대기 인원과 상담 수용률 변화를 함께 확인하세요.";
}
