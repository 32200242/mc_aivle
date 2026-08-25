"use client";

import { useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { DashboardRegion, DashboardSummary } from "@/lib/types";

const FEATURED_REGIONS = ["SEO", "GYE", "BUS", "INC", "DGU", "GWJ", "DJN"];
const OFFICIAL_PROJECT_BUDGET = 151_379_000_000;
const OFFICIAL_PREVIOUS_BUDGET = 145_197_000_000;
const OFFICIAL_PROJECT_CODE = "2356-432";
const OFFICIAL_BUDGET_ROWS = [
  ["가족센터 운영", 96_176_000_000, "센터 운영·평가, 다문화가족 자녀 지원, 결혼이민자 취업 및 취약·위기가족 지원"],
  ["공동육아나눔터 운영", 13_716_000_000, "지역 공동돌봄 공간과 자녀돌봄 품앗이 운영"],
  ["다문화가족 특성화사업", 34_069_000_000, "방문교육, 언어발달, 통번역, 이중언어 학습 및 결혼이민자 역량강화"],
  ["사회복무요원 배치지원", 400_000_000, "가족센터·다문화가족지원센터 배치인력 지원"],
  ["가족전용상담전화 운영", 5_947_000_000, "가족상담전화와 다누리콜센터 인건비·운영비"],
  ["다문화가족 사회통합 기반구축", 671_000_000, "결혼이민예정자 현지교육과 국외 다문화가족 지원"],
  ["전국다문화가족 실태조사", 400_000_000, "2026년 결혼중개업 실태조사"],
] as const;

type Quarter = {
  year: number;
  quarter: number;
  start: string;
  end: string;
};

type PerformanceRow = {
  label: string;
  unit: string;
  annualTarget: string;
  quarterTarget: string;
  actual: string;
  achievement: string;
  change: string;
};

export default function AdminReportsPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [selectedQuarterKey, setSelectedQuarterKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<DashboardSummary>("/admin/dashboard?days=365", { signal: controller.signal })
      .then(setData)
      .catch((reason: Error) => {
        if (reason.name !== "AbortError") setError(reason.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const quarterOptions = useMemo(() => data ? availableReportQuarters(data) : [], [data]);
  const selectedQuarter = useMemo(
    () => quarterOptions.find(quarter => quarterKey(quarter) === selectedQuarterKey) ?? quarterOptions[0] ?? null,
    [quarterOptions, selectedQuarterKey],
  );
  const report = useMemo(() => data && selectedQuarter ? buildReport(data, selectedQuarter) : null, [data, selectedQuarter]);

  return (
    <AppShell
      title="사업 실적 보고서"
      subtitle="가족센터 운영 데이터로 분기 실적 보고서를 자동 구성합니다."
      referenceDate={data?.data_as_of}
    >
      <div className="report-toolbar">
        <div className="report-toolbar-copy">
          <b>분기 운영 실적 보고</b>
          <span>전국 가족센터 운영자료를 기준으로 자동 구성된 분기 보고서입니다.</span>
        </div>
        <div className="report-toolbar-actions">
          <label className="report-period-select">
            <span>보고기간</span>
            <select
              value={selectedQuarter ? quarterKey(selectedQuarter) : ""}
              onChange={event => setSelectedQuarterKey(event.target.value)}
              disabled={!quarterOptions.length}
            >
              {quarterOptions.map(quarter => (
                <option key={quarterKey(quarter)} value={quarterKey(quarter)}>
                  {formatQuarter(quarter)}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => window.print()} disabled={!report}>▣ 인쇄 · PDF 저장</button>
        </div>
      </div>

      {error && <p className="dashboard-error">{error}</p>}
      {loading && !report && <div className="report-loading"><i /><b>보고서 양식을 구성하고 있습니다.</b><span>저장된 운영 실적을 불러오는 중입니다.</span></div>}

      {report && data && (
        <article className="admin-report-document">
          <header className="report-cover">
            <div className="report-document-line">
              <span>문서번호: 한건원-{report.asOf.slice(0, 4)}-{report.asOf.slice(5).replace("-", "")}</span>
              <b>내부결재</b>
            </div>
            <p>한국건강가정진흥원 · 전국 가족서비스 운영 총괄</p>
            <h1>{formatQuarter(report.quarter)} 전국 가족서비스 운영 실적 보고</h1>
            <span className="report-subtitle">전국 가족서비스 제공기관 운영·상담·성과관리 현황</span>
          </header>

          <table className="report-routing-table">
            <tbody>
              <tr><th>수 신</th><td>성평등가족부장관</td><th>참 조</th><td>가족정책관</td></tr>
              <tr><th>발 신</th><td>한국건강가정진흥원장</td><th>보고일</th><td>{formatKoreanDate(report.asOf)}</td></tr>
              <tr><th>보고기간</th><td colSpan={3}>{formatQuarter(report.quarter)} ({formatDotDate(report.quarter.start)} ~ {formatDotDate(report.quarter.end)})</td></tr>
            </tbody>
          </table>

          <ReportSection number="1" title="사업 개요">
            <DefinitionGrid items={[
              ["가. 사업 목적", "지역 특성을 고려한 맞춤형 가족지원서비스와 교육·상담·돌봄을 제공하여 가족의 안정성 강화와 가족관계 증진을 지원합니다."],
              ["나. 지원 대상", `전국 가족서비스 제공기관 ${data.center_count.toLocaleString()}개소`],
              ["다. 사업 기간", `${formatQuarter(report.quarter)} (${formatDotDate(report.quarter.start)} ~ ${formatDotDate(report.quarter.end)})`],
              ["라. 2026년 사업예산", `${report.totalBudget.toLocaleString()}원 (양성평등기금, 세부사업 ${OFFICIAL_PROJECT_CODE})`],
            ]} />
          </ReportSection>

          <ReportSection number="2" title="가족센터 운영 현황">
            <div className="report-table-scroll">
              <table className="report-data-table region-performance-table">
                <thead><tr><th>구분</th>{report.regionColumns.map(region => <th key={region.id}>{region.label}</th>)}</tr></thead>
                <tbody>
                  <tr><th>센터 수<br /><small>(개소)</small></th>{report.regionColumns.map(region => <td key={region.id}>{region.centers.toLocaleString()}</td>)}</tr>
                  <tr><th>상담인력<br /><small>(명)</small></th>{report.regionColumns.map(region => <td key={region.id}>{region.counselors.toLocaleString()}</td>)}</tr>
                  <tr><th>누적 상담 참여인원<br /><small>(명)</small></th>{report.regionColumns.map(region => <td key={region.id}>{region.sessions.toLocaleString()}</td>)}</tr>
                </tbody>
              </table>
            </div>
            <p className="report-table-note">※ 누적 상담 참여인원은 분기 중 상담에 참여한 인원을 지역별로 합산한 연인원입니다.</p>
          </ReportSection>

          <ReportSection number="3" title="주요 성과 지표 달성 현황">
            <div className="report-table-scroll">
              <table className="report-data-table performance-table">
                <thead><tr><th>성과 지표</th><th>단위</th><th>연간 목표</th><th>{report.quarter.quarter}/4분기 목표</th><th>실적</th><th>달성률</th><th>비교·기준</th></tr></thead>
                <tbody>{report.performanceRows.map(row => <tr key={row.label}><th>{row.label}</th><td>{row.unit}</td><td>{row.annualTarget}</td><td>{row.quarterTarget}</td><td><b>{row.actual}</b></td><td><span className="achievement-chip">{row.achievement}</span></td><td className={row.change.startsWith("▼") ? "report-down" : "report-up"}>{row.change}</td></tr>)}</tbody>
              </table>
            </div>
            <p className="report-table-note">※ 상담 참여인원과 만족도는 선택 분기 실적이며, 교육·평가·실습·기록시간은 보고서 기준일 현재 운영 현황입니다.</p>
          </ReportSection>

          <ReportSection number="4" title="사업예산 현황">
            <div className="report-finance-summary">
              <div><span>2026년 공식 사업예산</span><b>{formatWon(report.totalBudget)}</b></div>
              <div><span>2025년 예산</span><b>{formatWon(OFFICIAL_PREVIOUS_BUDGET)}</b></div>
              <div><span>전년 대비</span><b>+4.3%</b></div>
            </div>
            <div className="report-table-scroll">
              <table className="report-data-table official-budget-table">
                <thead><tr><th>사업 구분</th><th>2026년 예산</th><th>구성비</th><th>주요 범위</th></tr></thead>
                <tbody>
                  <tr className="report-total-row"><th>합 계</th><td>{report.totalBudget.toLocaleString()}원</td><td>100.0%</td><td>건강가정 및 다문화가족 지원</td></tr>
                  {OFFICIAL_BUDGET_ROWS.map(([label, budget, scope]) => <tr key={label}><th>{label}</th><td>{budget.toLocaleString()}원</td><td>{(budget / report.totalBudget * 100).toFixed(1)}%</td><td>{scope}</td></tr>)}
                </tbody>
              </table>
            </div>
            <p className="report-table-note report-source-note">
              ※ 예산액은 성평등가족부 2026년도 기금운용계획 「건강가정 및 다문화가족 지원」 연간 계획 기준임.
            </p>
          </ReportSection>

          <ReportSection number="5" title="주요 성과 및 우수사례">
            <Subsection title="가. 주요 성과">
              <ReportBullets items={[
                `${formatQuarter(report.quarter)} 누적 상담 참여인원 ${report.quarterSessions.toLocaleString()}명`,
                `이용자 만족도 ${report.satisfaction.toFixed(2)}점(5점 만점), 기준일 현재 사전·사후 완료율 ${data.pre_post_completion_rate.toFixed(1)}%`,
                `기준일 현재 상담인력 교육 이수율 ${data.training_completion_rate.toFixed(1)}%, 평균 상담 수용률 ${data.utilization_rate.toFixed(1)}%`,
                `AI 상담 실습 ${data.practice.completed_sessions.toLocaleString()}건 완료, 규칙 기반 평균 참고점수 변화 ${data.practice.average_score_change >= 0 ? "+" : ""}${data.practice.average_score_change.toFixed(1)}점`,
                `기준일 현재 상담기록 작성시간 건당 평균 ${data.ai_report_minutes.toFixed(1)}분`,
              ]} />
            </Subsection>
            <Subsection title="나. 우수사례">
              <div className="report-case-grid">
                <ReportCase area="서울 강남구 가족센터" title="AI 기반 초기상담 기록지원" text="상담 직후 기록 초안을 자동 구성해 행정 소요시간을 줄이고 사례회의 준비시간을 확보했습니다." />
                <ReportCase area="경기 수원시 가족센터" title="지역사회 조기연계 체계" text="복지·의료기관과 공통 의뢰 절차를 적용해 취약가족 지원 연결의 누락을 줄였습니다." />
                <ReportCase area="부산 해운대구 가족센터" title="야간·주말 상담 확대" text="직장인 가족을 위한 탄력 운영시간을 마련해 예약 선택권과 상담 접근성을 높였습니다." />
              </div>
            </Subsection>
          </ReportSection>

          <ReportSection number="6" title="운영상 보완사항 및 조치계획">
            <div className="report-table-scroll">
              <table className="report-data-table official-action-table">
                <thead><tr><th>구분</th><th>보완 필요사항</th><th>조치계획</th><th>완료 목표</th></tr></thead>
                <tbody>
                  <tr><th>서비스 접근성</th><td>농어촌·도서지역 등 이동 여건을 고려한 가족서비스 접근성 관리 필요</td><td>찾아가는 가족서비스 운영일정을 확대하고 권역 공동상담 일정을 정례화</td><td>{formatQuarter(report.nextQuarter)}</td></tr>
                  <tr><th>전문서비스 제공</th><td>상담·언어발달 등 전문인력의 지역별 수급 편차에 대한 지속 점검 필요</td><td>권역 내 전문인력 공동활용 기준을 마련하고 순회 전문가 운영을 시범 적용</td><td>{formatQuarter(report.nextQuarter)} 시범운영</td></tr>
                  <tr><th>시설·장비 관리</th><td>센터별 상담공간 및 디지털 장비 개선 수요의 우선순위 설정 필요</td><td>센터 수요조사 결과와 이용실적을 반영해 개선 우선순위를 확정하고 차년도 예산과 연계</td><td>{report.nextQuarter.year}년도 4/4분기</td></tr>
                </tbody>
              </table>
            </div>
          </ReportSection>

          <ReportSection number="7" title="향후 추진계획">
            <div className="report-table-scroll">
              <table className="report-data-table official-plan-table">
                <thead><tr><th>추진과제</th><th>세부 추진내용</th><th>추진일정</th><th>확인지표</th></tr></thead>
                <tbody>
                  <tr><th>가족위기 조기대응 강화</th><td>위기징후 확인 기준을 보완하고 고위험 사례의 상담·지역기관 연계 절차를 점검</td><td>{formatQuarter(report.nextQuarter)}</td><td>고위험 사례 연계 완료율</td></tr>
                  <tr><th>지역협력 연계체계 정비</th><td>복지관·의료기관 등 협력기관의 의뢰·회신 절차와 담당 창구를 현행화</td><td>{formatQuarter(report.nextQuarter)}</td><td>기관 연계 처리율</td></tr>
                  <tr><th>교육·상담 운영 다각화</th><td>가족교육의 온·오프라인 병행 운영과 야간·주말 상담 편성을 확대</td><td>{formatQuarter(report.nextQuarter)}</td><td>프로그램 참여율</td></tr>
                  <tr><th>종사자 역량강화</th><td>상담기록, 사례관리 및 개인정보보호를 중심으로 권역별 실무교육을 실시</td><td>{formatQuarter(report.nextQuarter)} 2회</td><td>교육 이수율·만족도</td></tr>
                </tbody>
              </table>
            </div>
          </ReportSection>

          <section className="report-attachments">
            <h2>붙 임</h2>
            <ol><li>가족센터별 세부 운영 실적 통계표 1부</li><li>권역별 성과 지표 달성 현황 1부</li><li>우수사례 상세 자료 1부</li></ol>
          </section>

          <footer className="report-signature">
            <span>{formatKoreanDate(report.asOf)}</span>
            <b>한국건강가정진흥원장</b>
            <i>(직인 생략)</i>
          </footer>
        </article>
      )}
    </AppShell>
  );
}

function ReportSection({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return <section className="report-section"><h2><span>{number}</span>{title}</h2>{children}</section>;
}

function Subsection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="report-subsection"><h3>{title}</h3>{children}</section>;
}

function DefinitionGrid({ items }: { items: Array<[string, string]> }) {
  return <dl className="report-definition-grid">{items.map(([term, description]) => <div key={term}><dt>{term}</dt><dd>{description}</dd></div>)}</dl>;
}

function ReportBullets({ items }: { items: string[] }) {
  return <ul className="report-bullets">{items.map(item => <li key={item}>{item}</li>)}</ul>;
}

function ReportCase({ area, title, text }: { area: string; title: string; text: string }) {
  return <article><span>{area}</span><b>{title}</b><p>{text}</p></article>;
}

function buildReport(data: DashboardSummary, quarter: Quarter) {
  const quarterTrend = data.trend.filter(row => row.date >= quarter.start && row.date <= quarter.end);
  const quarterSessions = quarterTrend.reduce((sum, row) => sum + row.sessions, 0);
  const satisfaction = quarterTrend.length
    ? quarterTrend.reduce((sum, row) => sum + row.satisfaction, 0) / quarterTrend.length
    : data.satisfaction;
  const previous = previousQuarter(quarter);
  const previousSessions = data.trend
    .filter(row => row.date >= previous.start && row.date <= previous.end)
    .reduce((sum, row) => sum + row.sessions, 0);
  const sessionChange = previousSessions ? (quarterSessions / previousSessions - 1) * 100 : data.changes.sessions;
  const annualTarget = data.service_targets.family_counseling_users;
  const quarterTarget = Math.round(annualTarget / 4);
  const performanceRows: PerformanceRow[] = [
    { label: "누적 상담 참여인원", unit: "명", annualTarget: formatNumber(annualTarget), quarterTarget: formatNumber(quarterTarget), actual: formatNumber(quarterSessions), achievement: percentage(quarterSessions, quarterTarget), change: changeLabel(sessionChange, "%") },
    { label: "이용자 만족도", unit: "점(5점)", annualTarget: "4.30", quarterTarget: "4.30", actual: satisfaction.toFixed(2), achievement: percentage(satisfaction, 4.3), change: changeLabel(data.changes.satisfaction, "점") },
    { label: "사전·사후 평가 완료(기준일)", unit: "%", annualTarget: "-", quarterTarget: "-", actual: data.pre_post_completion_rate.toFixed(1), achievement: "현황", change: `기준일 ${data.data_as_of}` },
    { label: "종사자 교육 이수(기준일)", unit: "%", annualTarget: "-", quarterTarget: "-", actual: data.training_completion_rate.toFixed(1), achievement: "현황", change: `기준일 ${data.data_as_of}` },
    { label: "AI 상담 실습 완료(기준일)", unit: "건", annualTarget: "-", quarterTarget: "-", actual: data.practice.completed_sessions.toLocaleString(), achievement: "현황", change: `평균 ${data.practice.average_score_change >= 0 ? "+" : ""}${data.practice.average_score_change.toFixed(1)}점` },
    { label: "상담기록 작성시간(기준일)", unit: "분/건", annualTarget: "-", quarterTarget: "-", actual: data.ai_report_minutes.toFixed(1), achievement: "현황", change: `기준일 ${data.data_as_of}` },
  ];

  const regionColumns = buildRegionColumns(data.regions, quarterSessions);
  const nextQuarter = quarter.quarter === 4 ? { year: quarter.year + 1, quarter: 1 } : { year: quarter.year, quarter: quarter.quarter + 1 };

  return {
    asOf: data.data_as_of,
    quarter,
    quarterSessions,
    satisfaction,
    performanceRows,
    regionColumns,
    totalBudget: OFFICIAL_PROJECT_BUDGET,
    nextQuarter,
  };
}

function buildRegionColumns(regions: DashboardRegion[], quarterSessions: number) {
  const totalSessions = regions.reduce((sum, region) => sum + region.sessions, 0) || 1;
  const selected = FEATURED_REGIONS.map(id => regions.find(region => region.id === id)).filter((region): region is DashboardRegion => Boolean(region));
  const others = regions.filter(region => !FEATURED_REGIONS.includes(region.id));
  const summarize = (id: string, label: string, items: DashboardRegion[]) => ({
    id,
    label,
    centers: items.reduce((sum, region) => sum + region.center_count, 0),
    counselors: items.reduce((sum, region) => sum + region.counselor_count, 0),
    sessions: Math.round(items.reduce((sum, region) => sum + region.sessions, 0) / totalSessions * quarterSessions),
  });
  return [
    summarize("TOTAL", "계", regions),
    ...selected.map(region => summarize(region.id, region.short_name, [region])),
    summarize("OTHER", "기타", others),
  ];
}

function latestCompletedQuarter(asOf: string): Quarter {
  const [currentYear, currentMonth] = asOf.split("-").map(Number);
  const currentQuarter = Math.floor((currentMonth - 1) / 3) + 1;
  const quarter = currentQuarter === 1 ? 4 : currentQuarter - 1;
  const year = currentQuarter === 1 ? currentYear - 1 : currentYear;
  return makeQuarter(year, quarter);
}

function availableReportQuarters(data: DashboardSummary) {
  const firstDate = data.trend[0]?.date ?? data.period_start;
  const targetYear = data.service_targets.year;
  const quarters: Quarter[] = [];
  let cursor = latestCompletedQuarter(data.data_as_of);

  for (let index = 0; index < 8 && cursor.end >= firstDate; index += 1) {
    if (cursor.start >= firstDate && cursor.year === targetYear) quarters.push(cursor);
    cursor = previousQuarter(cursor);
  }
  return quarters.length ? quarters : [latestCompletedQuarter(data.data_as_of)];
}

function previousQuarter(quarter: Quarter) {
  return quarter.quarter === 1
    ? makeQuarter(quarter.year - 1, 4)
    : makeQuarter(quarter.year, quarter.quarter - 1);
}

function makeQuarter(year: number, quarter: number): Quarter {
  const startMonth = (quarter - 1) * 3 + 1;
  const endMonth = startMonth + 2;
  const endDay = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
  return { year, quarter, start: isoDate(year, startMonth, 1), end: isoDate(year, endMonth, endDay) };
}

function quarterKey(quarter: Quarter) {
  return `${quarter.year}-Q${quarter.quarter}`;
}

function formatQuarter(quarter: Pick<Quarter, "year" | "quarter">) {
  return `${quarter.year}년도 ${quarter.quarter}/4분기`;
}

function isoDate(year: number, month: number, day: number) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function formatKoreanDate(value: string) {
  const [year, month, day] = value.split("-");
  return `${year}년 ${month}월 ${day}일`;
}

function formatDotDate(value: string) {
  return value.replaceAll("-", ".");
}

function formatNumber(value: number) {
  return Math.round(value).toLocaleString();
}

function formatWon(value: number) {
  return `${(value / 100_000_000).toLocaleString(undefined, { maximumFractionDigits: 1 })}억원`;
}

function percentage(actual: number, target: number) {
  return `${Math.round(actual / Math.max(target, 1) * 100)}%`;
}

function changeLabel(value = 0, unit: string) {
  const direction = value >= 0 ? "▲" : "▼";
  return `${direction} ${Math.abs(value).toFixed(1)}${unit}`;
}
