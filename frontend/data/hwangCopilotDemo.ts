import type { CopilotResult, IntegratedRecords, OCRResult, OCRStatus, ReportResult } from "@/lib/types";


export const HWANG_DEMO_CLIENT_ID = "client-00013";
export const HWANG_DEMO_IMAGE_URL = "/demo/hwang-jaehoon-couple-soap-handwritten-0829.png";
export const HWANG_NEXT_SESSION_AT = "2026-08-29T15:00:00+09:00";

export const HWANG_SESSION_TEXT = `내담자는 배우자와 대화를 시작하면 비난과 방어가 반복되고 갈등 후 관계를 회복하는 데 시간이 오래 걸린다고 보고함.
1회기 과제로 갈등 장면과 감정을 기록했으며, 대화를 중단한 뒤 다시 시도했을 때 언성이 낮아졌다고 설명함.
상담사는 갈등 순환을 함께 확인하고 감정-욕구-요청 문장으로 바꾸어 말하는 연습을 진행함.
최근 부부 갈등 중 신체적 폭력과 위협은 없었다고 보고했으며 즉각적인 위기 징후는 관찰되지 않음.`;

export const HWANG_OCR_TEXT = `S: 배우자와 생활비·육아 분담을 이야기하다 서로 말이 커졌지만, 20분 뒤 대화를 다시 했을 때 언성이 낮아졌다고 보고함. 신체적 폭력과 위협은 없었다고 보고함.
O: 초반에는 서로 말을 끊고 시선을 피함. 갈등 순환을 확인한 뒤 상대의 말을 끝까지 듣고 감정을 한 문장으로 표현함.
A: 생활비·육아 분담을 둘러싼 비난-방어 순환이 반복됨. 대화 중단 후 재시도 경험은 관계 회복의 보호요인으로 보임.
P: 대화 중단 신호와 20분 뒤 재개 규칙을 적용하기로 함. 생활비·육아 분담 요청을 각각 한 문장으로 작성하기로 함. 다음 상담은 2026년 8월 29일 오후 3시에 진행하기로 함.`;

export const HWANG_OCR_REVIEW_NOTE = "부부 갈등 내용과 신체적 폭력·위협 관련 부정문을 수기 원본과 문장 단위 대조 완료";
export const HWANG_EXISTING_SUMMARY = "1회기에서 비난-방어 순환을 확인하고 감정과 요청을 구분해 표현하는 것을 초기 목표로 합의함.";

export const HWANG_OCR_STATUS: OCRStatus = {
  provider: "document_review",
  available: true,
  detail: "문서 인식 준비됨",
  gpu_available: true,
  model_id: null,
  review_required: true,
};

export const HWANG_OCR_RESULT: OCRResult = {
  provider: "document_review",
  raw_text: HWANG_OCR_TEXT,
  clean_text: HWANG_OCR_TEXT,
  warnings: [],
  requires_review: true,
  risk_review_required: true,
  omission_suspected: false,
  review_reasons: ["신체적 폭력과 위협 관련 부정 문장을 원본과 대조함"],
  benchmark_notice: "",
  pages: [{
    page: "황재훈_2회기_SOAP_수기.png",
    detected_form: "SOAP 일지",
    raw_text: HWANG_OCR_TEXT,
    clean_text: HWANG_OCR_TEXT,
    tokens: [],
    alternate_text: null,
    review_reasons: ["부부 갈등 중 폭력·위협 관련 부정 표현 확인"],
    risk_terms: ["신체적 폭력", "위협", "없었다고"],
    omission_suspected: false,
  }],
};

export const HWANG_COPILOT_RESULT: CopilotResult = {
  provider: "prepared_case",
  model: "prepared_case",
  generation_mode: "mock",
  fallback_reason: null,
  source_type: "synthetic_case",
  client_id: HWANG_DEMO_CLIENT_ID,
  session_number: 2,
  analysis_mode: "cumulative",
  source_scope: ["사전문진", "1회기 확정기록"],
  summary: "황재훈 내담자는 대화를 시작할 때 비난과 방어가 반복되고 갈등 후 회복이 늦어지는 순환을 보고했습니다. 2회기에서는 안전 여부를 다시 확인한 뒤 갈등 중단과 복구 대화를 구체적으로 연습하는 것이 적절합니다.",
  core_issues: ["비난-방어 상호작용의 반복", "갈등 후 관계 복구 지연"],
  observed_emotions: ["1회기 초반 긴장", "반복 갈등에서의 답답함과 경계"],
  risk_signals: ["관계 해체 고려 문항 1/3 응답", "즉각적 위기 징후는 없으나 매 회기 안전 여부 직접 확인"],
  recommended_directions: [
    "최근 갈등 한 장면을 시작-반응-결과 순서로 재구성하기",
    "비난 문장을 감정-욕구-구체적 요청 문장으로 전환해 연습하기",
    "대화 중단 신호와 20분 이내 복구 대화 절차를 합의하기",
  ],
  suggested_questions: [
    "최근 갈등에서 가장 먼저 달라진 말투나 행동은 무엇이었나요?",
    "대화를 다시 시작해도 안전하다고 느끼게 하는 상대의 반응은 무엇인가요?",
    "이번 주 한 번 시도할 수 있는 가장 작은 복구 행동은 무엇인가요?",
  ],
  recommended_phrases: [
    "누가 옳은지보다 두 분의 대화가 어떤 순서로 막히는지 함께 살펴보겠습니다.",
    "비난 대신 지금 느끼는 감정과 원하는 요청을 한 문장으로 바꿔볼까요?",
  ],
  avoid_phrases: [
    "두 분은 원래 의사소통이 안 되는 유형입니다.",
    "한쪽이 먼저 참으면 해결됩니다.",
  ],
  soap_draft: {},
  module_analyses: [
    {
      id: "intake_pattern",
      title: "사전문진 통합",
      frameworks: ["FRPS", "FSTRESS", "관계 해체 고려 문항"],
      evidence_level: "누적기록 기반",
      summary: "관계 부담과 생활사건 부담을 진단값이 아닌 면담 우선순위로 함께 검토합니다.",
      evidence: ["가족관계 문제징후 47/90 · 확인 기준 54", "생활사건 경험빈도·부담 합계 분리 확인", "관계 해체 고려 문항 1/3"],
      hypotheses: ["최근 반복 갈등이 관계 부담 응답에 영향을 주었을 가능성"],
      questions: ["점수에 답할 때 가장 먼저 떠올린 최근 갈등 장면은 무엇이었나요?"],
      limitation: "사전문진은 자기보고 참고자료이며 위험등급이나 관계 예후를 확정하지 않습니다.",
    },
    {
      id: "safety_priority",
      title: "안전·우선확인",
      frameworks: ["가족위기 선별", "기관 위기대응 절차"],
      evidence_level: "누적기록 기반",
      summary: "즉각적 위기 징후는 기록되지 않았지만 관계 해체 고려 응답과 현재 안전을 직접 다시 확인합니다.",
      evidence: ["1회기 기록: 현재 확인된 즉각적 위기 징후 없음", "관계 해체 고려 문항 1/3"],
      hypotheses: ["갈등 강도가 높아질 때 안전감과 관계 지속 의사가 달라질 수 있음"],
      questions: ["최근 본인이나 가족의 안전이 위협받는 순간이 있었나요?", "갈등이 심해질 때 연락할 수 있는 사람은 누구인가요?"],
      limitation: "안전 여부는 자동 판정하지 않고 상담사의 직접 질문과 기관 절차로 확인합니다.",
    },
    {
      id: "relationship_lenses",
      title: "관계패턴 이해",
      frameworks: ["Bowen", "구조적 가족치료"],
      evidence_level: "누적기록 기반",
      summary: "대화 시작 후 비난과 방어가 이어지고 회복이 지연되는 상호작용 순환을 탐색합니다.",
      evidence: ["1회기 내담자 보고: 비난과 방어가 이어짐", "1회기 개입: 갈등 순환 도식화"],
      hypotheses: ["감정 표현 방식과 생활 역할 기대의 차이가 순환을 강화할 가능성"],
      questions: ["갈등이 시작되어 멈출 때까지 두 분은 어떤 순서로 반응하나요?"],
      limitation: "이론은 관계유형 판정이 아니라 다음 면담에서 확인할 가설입니다.",
    },
    {
      id: "intervention_lenses",
      title: "개입 관점",
      frameworks: ["EFT", "해결중심"],
      evidence_level: "누적기록 기반",
      summary: "핵심 감정과 관계 욕구를 구체적 요청으로 바꾸고, 갈등이 덜했던 예외 장면을 복구 대화에 활용합니다.",
      evidence: ["상담 목표: 비난 없이 감정과 요청 표현", "보호요인: 갈등이 낮을 때 협력 경험이 있음"],
      hypotheses: ["작은 복구 성공을 구체화하면 대화 재시도 가능성이 높아질 수 있음"],
      questions: ["문제가 덜했던 날에는 두 분의 첫 반응이 무엇이 달랐나요?"],
      limitation: "개입은 내담자의 반응과 안전 확인 결과에 따라 상담사가 조정합니다.",
    },
  ],
  xai_notice: "사전문진 점수와 1회기 확정기록에 직접 적힌 근거만 표시했습니다. 이론별 내용은 진단이나 자동 처방이 아니라 2회기에서 검증할 가설입니다.",
};

export function buildHwangRecords(serviceDate: string): IntegratedRecords {
  return {
    provider: "prepared_case",
    model: "prepared_case",
    generation_mode: "mock",
    fallback_reason: null,
    initial_intake: {},
    session_record: {
      "상담자": "윤주연 상담사",
      "내담자": "황재훈, 배우자",
      "상담일자": serviceDate,
      "상담시작시각": "09:00",
      "상담종료시각": "09:50",
      "상담회기": "2",
      "접수 연계기관": "",
      "상담방법": "면접상담",
      "상담유형": "부부상담",
      "상담주제 1순위": "부부 의사소통 및 반복 갈등",
      "상담주제 2순위": "갈등 후 복구 대화",
      "상담주제 3순위": "감정과 요청 표현",
      "당회기 상담목표": "비난-방어 순환을 멈추고 감정-욕구-요청 문장으로 복구 대화를 연습한다.",
      "상담내용(상담개입)": "생활비와 육아 분담을 둘러싼 최근 갈등 장면을 시작-반응-결과 순서로 재구성하였다. 두 사람은 초반에 서로의 말을 끊고 시선을 피했으나, 갈등 순환을 확인한 뒤 상대의 말을 끝까지 듣고 감정을 한 문장으로 표현하였다. 대화를 중단한 뒤 20분 후 다시 시도했을 때 언성이 낮아진 경험을 확인했으며, 신체적 폭력과 위협은 없었다고 보고하였다.",
      "다음 회기 계획": "대화 중단 신호와 20분 이내 복구 대화 절차의 실행 결과를 확인하고 생활 역할 기대를 구체적으로 조율한다.",
      "연계기관": "현재 연계 없음",
    },
    soap: {
      "S": "배우자와 생활비·육아 분담을 이야기하다 서로 말이 커졌지만, 20분 뒤 대화를 다시 했을 때 언성이 낮아졌다고 보고함. 신체적 폭력과 위협은 없었다고 보고함.",
      "O": "초반에는 서로 말을 끊고 시선을 피함. 갈등 순환을 확인한 뒤 상대의 말을 끝까지 듣고 감정을 한 문장으로 표현함.",
      "A": "생활비·육아 분담을 둘러싼 비난-방어 순환이 반복됨. 대화 중단 후 재시도 경험은 관계 회복의 보호요인으로 보임.",
      "P": "대화 중단 신호와 20분 뒤 재개 규칙을 적용하기로 함. 생활비·육아 분담 요청을 각각 한 문장으로 작성하기로 함. 다음 상담은 2026년 8월 29일 오후 3시에 진행하기로 함.",
    },
    uncertain_items: ["신체적 폭력·위협·강압 여부는 매 회기 상담사가 직접 확인합니다."],
    source_summary: {
      "상담 대화": "2회기 고정 시연 메모 반영",
      "OCR 기록": "수기 SOAP 자료 반영",
      "OCR 원본 검수": "문장 단위 대조 완료",
      "OCR 검수 메모": HWANG_OCR_REVIEW_NOTE,
      "사례관리 기본정보": "황재훈 사례 연결",
      "1회기 확정기록": "반영됨",
    },
  };
}

export function buildHwangReport(serviceDate: string): ReportResult {
  return {
    provider: "prepared_case",
    model: "prepared_case",
    generation_mode: "mock",
    fallback_reason: null,
    session_report: `[2회기 요약 · ${serviceDate} 09:00~09:50]\n내담자 부부는 생활비와 육아 분담을 둘러싼 갈등 장면을 재구성하고 비난-방어 순환을 확인하였다. 초반에는 서로 말을 끊고 시선을 피했으나, 순환을 확인한 뒤 상대의 말을 끝까지 듣고 감정을 한 문장으로 표현하였다. 대화를 중단하고 20분 뒤 다시 시도했을 때 언성이 낮아진 경험을 관계 회복의 보호요인으로 확인하였다. 신체적 폭력과 위협은 없었다고 보고하였다.`,
    closing_report: "[중간평가 초안]\n비난 없이 감정과 요청을 표현하는 초기 목표는 부분 달성 단계이다. 다음 회기에는 대화 중단·재개 규칙의 실행 결과와 생활비·육아 분담 요청의 구체성을 확인한다.",
    review_notice: "확정 전 상담사가 원기록과 직접 관찰 내용을 대조해 주세요.",
  };
}
