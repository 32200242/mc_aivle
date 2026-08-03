import AppShell from "@/components/AppShell";
import { Panel, Tag } from "@/components/UI";

export default function AnalyticsPage() {
  return <AppShell title="종합 결과 및 예측" subtitle="성과 및 개선 우선순위를 예측합니다.">
    <div className="filter-row"><button>전국 전체⌄</button><button>2026년⌄</button><button>3분기⌄</button><button className="primary">분석 실행</button></div>
    <Panel><div className="panel-heading"><h2>예측 결과</h2><Tag tone="purple">2026년 12월까지</Tag></div><div className="prediction"><div><small>종합 성과 예측 점수</small><strong>88.7점</strong><span>전년 대비 ▲ 4.6점</span></div><svg viewBox="0 0 700 170"><polyline points="10,130 70,136 130,112 190,116 250,92 310,102 370,70" fill="none" stroke="#4777e5" strokeWidth="5"/><polyline points="370,70 430,95 490,78 550,60 610,68 690,48" fill="none" stroke="#a84fe1" strokeWidth="5" strokeDasharray="9 8"/></svg><div className="insight"><b>예측 인사이트</b><p>상담 만족도와 이용자 만족도 개선이 종합점수 상승 요인으로 분석됩니다.</p></div></div></Panel>
    <div className="two-col"><Panel><h2>영역별 성과</h2><table><tbody><tr><th>상담 서비스 운영</th><td>87.2</td><td>▲ 5.1</td></tr><tr><th>종사자 전문성</th><td>85.6</td><td>▲ 4.3</td></tr><tr><th>이용자 만족도</th><td>88.3</td><td>▲ 4.7</td></tr><tr><th>지역사회 협력체계</th><td>82.4</td><td>▲ 3.5</td></tr></tbody></table></Panel><Panel><h2>개선 우선순위 TOP 5</h2><ol className="priority-list"><li><b>1</b><span>기관 운영관리</span><progress value="82" max="100"/></li><li><b>2</b><span>상담 서비스 운영</span><progress value="67" max="100"/></li><li><b>3</b><span>종사자 전문성 강화</span><progress value="50" max="100"/></li><li><b>4</b><span>지역사회 협력체계</span><progress value="39" max="100"/></li><li><b>5</b><span>이용자 만족도</span><progress value="25" max="100"/></li></ol></Panel></div>
  </AppShell>;
}
