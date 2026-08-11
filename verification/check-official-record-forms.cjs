const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const baseUrl = process.env.VISUAL_BASE_URL || "http://127.0.0.1:3000";
const outputDir = path.resolve(__dirname, "../tmp/pdfs");
const longSessionContent = "내담자가 갈등 장면을 설명하고 상담자는 확인된 감정과 상호작용을 반영하였다. ".repeat(8).slice(0, 295);

const analysisResult = {
  provider: "verification", model: "verification", generation_mode: "model", fallback_reason: null,
  source_type: "linked_case", client_id: "verification", session_number: 1, analysis_mode: "cumulative",
  source_scope: ["확정 기록"], summary: "기록지 렌더링 검증용 분석입니다.",
  core_issues: ["의사소통"], observed_emotions: ["긴장"], risk_signals: ["직접 확인"],
  recommended_directions: ["확인된 내용을 중심으로 기록합니다."], suggested_questions: ["최근 상황을 설명해 주세요."],
  recommended_phrases: ["말씀하신 내용을 확인하겠습니다."], avoid_phrases: ["단정하지 않습니다."], soap_draft: {},
  module_analyses: [], xai_notice: "확정 기록을 기준으로 정리했습니다.",
};

const initialRecords = {
  provider: "verification", model: "verification", generation_mode: "model", fallback_reason: null,
  initial_intake: {
    "상담자": "윤주연 상담사", "상담일자": "2026-08-24", "상담시작시각": "16:00", "상담종료시각": "16:50",
    "상담방법": "면접상담", "상담유형": "부부상담", "사례번호": "FC-2026-004",
    "내담자1 성명": "오지아", "내담자1 관계": "본인", "내담자1 성별": "여",
    "내담자2 성명": "", "내담자2 관계": "배우자", "내담자2 성별": "남",
    "내담자3 성명": "", "내담자3 관계": "", "내담자3 성별": "", "내담자": "오지아", "상담회기": "1",
    "내담자 호소문제(주제)": "부부 의사소통에서 반복되는 갈등을 호소함.",
    "상담목표(내담자와 합의된 목표)": "갈등 상황에서 감정을 구체적으로 표현하는 것을 공동 목표로 정함.",
    "상담계획": "반복 갈등 장면과 상호작용을 확인하고 감정 표현을 연습함.",
    "상담내용": "내담자 보고와 상담 중 확인된 관계 맥락을 구분하여 기록함.",
    "가계도": "배우자(35세), 자녀 2명과 동거",
  },
  session_record: {}, soap: {}, uncertain_items: [], source_summary: { "사례관리": "연결됨" },
};

const sessionRecords = {
  provider: "verification", model: "verification", generation_mode: "model", fallback_reason: null,
  initial_intake: {},
  session_record: {
    "상담자": "윤주연 상담사", "내담자": "김민지, 배우자", "상담일자": "2026-08-11",
    "상담시작시각": "", "상담종료시각": "", "상담회기": "4", "접수 연계기관": "",
    "상담방법": "면접상담", "상담유형": "부부상담", "사례번호": "FC-2026-001",
    "내담자1 성명": "김민지", "내담자1 관계": "본인", "내담자1 성별": "여",
    "내담자2 성명": "", "내담자2 관계": "", "내담자2 성별": "",
    "내담자3 성명": "", "내담자3 관계": "", "내담자3 성별": "",
    "상담주제 1순위": "부부 의사소통", "상담주제 2순위": "역할 분담", "상담주제 3순위": "",
    "당회기 상담목표": "갈등 장면에서 서로의 감정과 요구를 구체적으로 확인함.",
    "상담내용(상담개입)": longSessionContent,
    "다음 회기 계획": "합의한 감정 표현 연습 결과를 점검함.", "연계기관": "",
  },
  soap: {}, uncertain_items: [], source_summary: { "현재 회기 데이터": "반영됨" },
};

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  const corsHeaders = {
    "access-control-allow-origin": baseUrl,
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "authorization, content-type",
  };
  await page.route("**/api/v1/copilot/analyze-case", route => route.fulfill({
    status: 200, contentType: "application/json", headers: corsHeaders,
    body: JSON.stringify(analysisResult),
  }));
  await page.route("**/api/v1/documents/records/generate", route => {
    const request = route.request().postDataJSON();
    const body = request.record_type === "initial_intake" ? initialRecords : sessionRecords;
    return route.fulfill({ status: 200, contentType: "application/json", headers: corsHeaders, body: JSON.stringify(body) });
  });

  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("CNS-SEO-00001");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor");
  await page.goto(`${baseUrl}/counselor/copilot`, { waitUntil: "networkidle" });

  const clientSelect = page.getByLabel("내담자");
  await clientSelect.selectOption("client-004");
  await page.getByRole("button", { name: "사전문진으로 1회기 분석", exact: true }).click();
  await page.getByRole("button", { name: "초기상담기록지 초안 생성", exact: true }).waitFor();
  await page.locator(".session-source-input textarea").fill("초기상담 기록 인쇄 검증");
  await page.getByRole("button", { name: "초기상담기록지 초안 생성", exact: true }).click();
  await page.locator(".initial-record-form").waitFor();
  await page.emulateMedia({ media: "print" });
  const initialPrint = await page.evaluate(() => ({
    sourceDisplay: getComputedStyle(document.querySelector(".genogram-source-label")).display,
    noteDisplay: getComputedStyle(document.querySelector(".genogram-official-note")).display,
    textareaDisplay: getComputedStyle(document.querySelector(".record-screen-textarea")).display,
    valueDisplay: getComputedStyle(document.querySelector(".record-print-value")).display,
  }));
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.pdf({ path: path.join(outputDir, "verified-initial-record.pdf"), format: "A4", printBackground: true, preferCSSPageSize: true });

  await page.emulateMedia({ media: "screen" });
  await clientSelect.selectOption("client-001");
  await page.locator(".case-identity-card small").filter({ hasText: "FC-2026-001" }).waitFor();
  await page.getByLabel("분석 기준 회기").selectOption("4");
  await page.getByRole("button", { name: "누적 기록으로 4회기 분석", exact: true }).waitFor();
  await page.getByRole("button", { name: "누적 기록으로 4회기 분석", exact: true }).click();
  await page.getByRole("button", { name: "상담기록지 초안 생성", exact: true }).waitFor();
  await page.locator(".session-source-input textarea").fill("상담기록지 인쇄 검증을 위한 현재 회기 기록");
  await page.getByRole("button", { name: "상담기록지 초안 생성", exact: true }).click();
  await page.locator(".session-record-form").waitFor();
  const interventionHeader = page.locator(".session-record-form th").filter({ hasText: "상담 내용" }).first();
  const rowSpan = await interventionHeader.getAttribute("rowspan");
  const maxLength = await page.locator(".session-record-form .record-screen-textarea").first().getAttribute("maxlength");
  await page.emulateMedia({ media: "print" });
  const hiddenEditors = await page.locator(".session-record-form .record-screen-textarea").evaluateAll(items => items.every(item => getComputedStyle(item).display === "none"));
  const visiblePrintValues = await page.locator(".session-record-form .record-print-value").evaluateAll(items => items.every(item => getComputedStyle(item).display === "block"));
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.pdf({ path: path.join(outputDir, "verified-session-record.pdf"), format: "A4", printBackground: true, preferCSSPageSize: true });

  const result = { initialPrint, rowSpan, maxLength, hiddenEditors, visiblePrintValues, errors };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (initialPrint.sourceDisplay !== "none" || initialPrint.noteDisplay === "none" || initialPrint.textareaDisplay !== "none" || initialPrint.valueDisplay !== "block" || rowSpan !== "3" || maxLength !== "300" || !hiddenEditors || !visiblePrintValues || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
