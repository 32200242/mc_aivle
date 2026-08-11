import type { AssessmentScore, QuestionnaireResponse } from "@/lib/types";


type AssessmentSummaryProps = {
  assessments: AssessmentScore[];
  responses?: QuestionnaireResponse[];
  compact?: boolean;
};

const BFI_DIMENSIONS = [
  { source: "BFI10-O", label: "새로운 관점 탐색", invert: false },
  { source: "BFI10-C", label: "계획·과제 수행", invert: false },
  { source: "BFI10-E", label: "대화 주도성", invert: false },
  { source: "BFI10-A", label: "상대 관점 수용", invert: false },
  { source: "BFI10-ES", label: "정서 민감성", invert: true },
] as const;

const FRPS_THEMES = [
  { label: "갈등·공격적 상호작용", items: ["FRPS_01", "FRPS_03", "FRPS_08", "FRPS_15", "FRPS_16", "FRPS_17"], prompt: "갈등이 시작되는 말과 행동, 강압이나 비꼼이 반복되는 장면을 확인" },
  { label: "회피·대화단절", items: ["FRPS_02", "FRPS_05", "FRPS_07", "FRPS_09", "FRPS_18"], prompt: "대화가 중단되는 상황과 먼저 대화를 피하는 가족원을 확인" },
  { label: "정서적 거리·친밀감 저하", items: ["FRPS_04", "FRPS_06", "FRPS_10", "FRPS_11", "FRPS_14"], prompt: "함께하는 시간과 애정 표현이 줄어든 시점과 예외 장면을 확인" },
  { label: "가족 내 편안함·상호관심", items: ["FRPS_12", "FRPS_13"], prompt: "집에서 느끼는 긴장과 서로의 어려움을 나누기 힘든 이유를 확인" },
] as const;

const FSTRESS_AREAS = [
  { label: "가족 형성·생활 전환", items: [1, 2, 3, 4, 5, 6, 14, 16, 17, 24, 25, 29, 30, 31] },
  { label: "자녀·가족 돌봄", items: [13, 15, 32, 33, 34, 35, 42] },
  { label: "가족관계", items: [7, 8, 9, 10, 36, 37, 38] },
  { label: "경제·직업", items: [18, 19, 20, 21, 22, 23, 39, 40, 41] },
  { label: "상실·건강", items: [11, 12, 26, 43] },
  { label: "안전·일탈·중독", items: [27, 28, 44, 45] },
] as const;


export default function AssessmentSummary({ assessments, responses = [], compact = false }: AssessmentSummaryProps) {
  const byCode = new Map(assessments.map(item => [item.code, item]));
  const frps = byCode.get("FRPS");
  const stress = byCode.get("FSTRESS");
  const divorce = byCode.get("DIVORCE");
  const relationship = relationshipSummary(frps, responses);
  const lifeEvents = lifeEventSummary(stress, responses);
  const personality = personalitySummary(byCode);

  return <>
    <div className={`assessment-insight-grid ${compact ? "compact" : ""}`}>
      <InsightCard
        eyebrow="관계에서 확인할 장면"
        title="가족관계 문제징후"
        summary={relationship.summary}
        prompt={relationship.prompt}
        evidence={relationship.evidence}
      />
      <InsightCard
        eyebrow="현재 부담으로 응답한 내용"
        title="생활사건 경험과 부담"
        summary={lifeEvents.summary}
        prompt={lifeEvents.prompt}
        evidence={lifeEvents.evidence}
      />
      <InsightCard
        eyebrow="대화 방식 참고"
        title="응답상 성격 경향"
        summary={personality.summary}
        prompt={personality.prompt}
        evidence="BFI-10 10문항 · 개인 내 차원 비교"
      />
      <InsightCard
        eyebrow="직접 확인이 필요한 응답"
        title="관계 해체 고려"
        summary={divorce ? `현재 응답: ‘${divorce.severity}’` : "현재 응답 없음"}
        prompt={divorce && divorce.score > 0 ? "생각의 빈도, 구체적인 의도·계획과 현재 안전을 직접 확인" : "최근 생각의 변화와 관계 회복 의지를 면담에서 확인"}
        evidence={divorce ? `단일 응답 ${formatScore(divorce.score)}/${formatScore(divorce.max_score)}` : "DIVORCE 응답 없음"}
        tone="caution"
      />
    </div>
    <p className="assessment-summary-note">사전문진에서 두드러진 응답을 면담 준비용으로 정리함. 진단이나 위험등급이 아니므로 원응답과 실제 면담 내용을 함께 확인.</p>
  </>;
}


function relationshipSummary(frps: AssessmentScore | undefined, responses: QuestionnaireResponse[]) {
  const responseById = new Map(responses.filter(item => item.section === "FRPS").map(item => [item.item_id, item.response_value]));
  const rankedThemes = FRPS_THEMES.flatMap(theme => {
    const values = theme.items.flatMap(itemId => responseById.has(itemId) ? [responseById.get(itemId)!] : []);
    return values.length ? [{ ...theme, average: values.reduce((sum, value) => sum + value, 0) / values.length }] : [];
  }).sort((a, b) => b.average - a.average);
  const leading = rankedThemes[0];
  if (!frps) {
    return {
      summary: "관계 갈등과 의사소통에 관한 응답 없음\n면담에서 구체적인 장면 확인 필요",
      prompt: "언제, 어떤 말에서 이런 패턴이 가장 자주 시작되는지 확인",
      evidence: "가족관계 문제징후 응답 없음",
    };
  }
  const criterion = frps.score >= 54 ? "확인 기준(54점) 이상" : "확인 기준(54점) 미만";
  const themeText = leading ? `\n상담 준비용 문항 묶음 중 ‘${leading.label}’ 응답이 상대적으로 높게 나타남` : "";
  return {
    summary: `총 ${formatScore(frps.score)}/90점 · ${criterion}${themeText}`,
    prompt: leading?.prompt ?? "높게 응답한 문항의 실제 장면과 반복 빈도를 확인",
    evidence: `총점 ${formatScore(frps.score)}/90 · 확인 기준 54`,
  };
}


function lifeEventSummary(stress: AssessmentScore | undefined, responses: QuestionnaireResponse[]) {
  const eventResponses = responses.filter(item => item.section === "FSTRESS");
  const experienced = eventResponses.filter(item => item.response_value > 0);
  const responseById = new Map(eventResponses.map(item => [item.item_id, item.response_value]));
  const rankedAreas = FSTRESS_AREAS.map(area => {
    const values = area.items.map(number => responseById.get(`FSTRESS_${String(number).padStart(2, "0")}`) ?? 0).filter(value => value > 0);
    return { ...area, count: values.length, burden: values.reduce((sum, value) => sum + value, 0) };
  }).filter(area => area.count > 0).sort((a, b) => b.burden - a.burden || b.count - a.count);
  const leading = rankedAreas[0];
  if (!stress) {
    return {
      summary: "최근 생활사건 응답 없음\n경험 여부와 사건별 부담 확인 필요",
      prompt: "사건의 발생 시점과 현재까지 이어지는 영향을 확인",
      evidence: "가족스트레스 응답 없음",
    };
  }
  if (!eventResponses.length) {
    const count = stress.severity.match(/\d+/)?.[0];
    return {
      summary: count
        ? `생활사건 ${count}건 경험 · 부담 합계 ${formatScore(stress.score)}/225점`
        : `생활사건 부담 합계 ${formatScore(stress.score)}/225점`,
      prompt: "사건의 발생 시점과 현재까지 이어지는 영향, 현재 안전을 구분하여 확인",
      evidence: count ? `경험빈도 ${count}/45 · 부담 합계 ${formatScore(stress.score)}/225` : `부담 합계 ${formatScore(stress.score)}/225`,
    };
  }
  const areaText = leading ? `\n가장 큰 부담 영역: ‘${leading.label}’ ${leading.count}건 · ${leading.burden}점` : "\n경험했다고 응답한 생활사건 없음";
  return {
    summary: `생활사건 ${experienced.length}건 경험 · 부담 합계 ${formatScore(stress.score)}/225점${areaText}`,
    prompt: "사건의 발생 시점과 현재까지 이어지는 영향, 현재 안전을 구분하여 확인",
    evidence: `경험빈도 ${experienced.length}/45 · 부담 합계 ${formatScore(stress.score)}/225`,
  };
}


function InsightCard({ eyebrow, title, summary, prompt, evidence, tone = "default" }: { eyebrow: string; title: string; summary: string; prompt: string; evidence: string; tone?: "default" | "caution" }) {
  return <article className={tone === "caution" ? "caution" : ""}>
    <small>{eyebrow}</small>
    <h3>{title}</h3>
    <p className="assessment-main-insight">{summary}</p>
    <div className="assessment-interview-prompt"><b>면담 확인</b><span>{prompt}</span></div>
    <em>{evidence}</em>
  </article>;
}


function personalitySummary(byCode: Map<string, AssessmentScore>) {
  const dimensions = BFI_DIMENSIONS.flatMap(dimension => {
    const item = byCode.get(dimension.source);
    if (!item) return [];
    return [{ label: dimension.label, score: dimension.invert ? item.max_score + 1 - item.score : item.score }];
  }).sort((a, b) => b.score - a.score);
  if (!dimensions.length) return { summary: "성격 경향 응답 없음", prompt: "실제 대화 속 반응과 선호하는 질문 방식을 확인" };
  const high = dimensions[0];
  const low = dimensions[dimensions.length - 1];
  return {
    summary: `‘${high.label}’ 경향이 상대적으로 두드러짐\n‘${low.label}’ 경향은 낮게 나타남`,
    prompt: "성격을 단정하지 않고 질문 속도, 과제 방식과 감정 표현 선호를 확인",
  };
}


function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
