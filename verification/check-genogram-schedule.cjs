const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const baseUrl = process.env.VISUAL_BASE_URL || "http://127.0.0.1:3000";
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
    status: 200,
    contentType: "application/json",
    headers: corsHeaders,
    body: JSON.stringify({
      provider: "verification", model: "verification", generation_mode: "model", fallback_reason: null,
      source_type: "linked_case", client_id: "client-00008", session_number: 1, analysis_mode: "pre_intake",
      source_scope: ["사전문진"], summary: "첫 상담에서 관계 갈등과 안전 여부를 확인합니다.",
      core_issues: ["의사소통"], observed_emotions: ["확인 필요"], risk_signals: ["직접 확인"],
      recommended_directions: ["호소문제를 구체적으로 확인합니다."], suggested_questions: ["최근 갈등 상황을 설명해 주세요."],
      recommended_phrases: ["천천히 말씀해 주세요."], avoid_phrases: ["누가 잘못했나요?"], soap_draft: {},
      module_analyses: [], xai_notice: "사전문진 자료를 기준으로 정리했습니다.",
    }),
  }));
  await page.route("**/api/v1/documents/records/generate", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    headers: corsHeaders,
    body: JSON.stringify({
      provider: "verification", model: "verification", generation_mode: "model", fallback_reason: null,
      initial_intake: {
        "상담자": "윤주연", "상담일자": "2026-08-11", "상담시작시각": "15:30", "상담종료시각": "16:20",
        "상담방법": "면접상담", "상담유형": "부부상담", "사례번호": "FC-2026-00008",
        "내담자1 성명": "최민주", "내담자1 관계": "본인", "내담자1 성별": "여",
        "내담자2 성명": "", "내담자2 관계": "", "내담자2 성별": "",
        "내담자3 성명": "", "내담자3 관계": "", "내담자3 성별": "", "내담자": "최민주", "상담회기": "1",
        "내담자 호소문제(주제)": "부부 의사소통에서 반복되는 갈등을 호소함.",
        "상담목표(내담자와 합의된 목표)": "갈등 상황의 상호작용을 확인함.",
        "상담계획": "초기 면담과 관계 맥락 확인", "상담내용": "내담자 보고와 사전문진을 확인함.",
        "가계도": "배우자(35세), 자녀 2명과 동거",
      },
      session_record: {}, soap: {}, uncertain_items: [], source_summary: { "사례관리": "연결됨" },
    }),
  }));

  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("CNS-SEO-00001");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor");

  const browserTodayKey = await page.evaluate(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  });
  const initiallySelectedDate = await page.locator('.schedule-calendar-day[aria-pressed="true"]').getAttribute("data-date");
  const defaultScheduleCount = await page.locator(".schedule-list .appointment").count();
  await page.screenshot({ path: path.join(__dirname, "counselor-today-schedule.png"), fullPage: true });
  const scheduledDay = page.locator(".schedule-calendar-day.has-appointments").first();
  await scheduledDay.click();
  const selectedScheduledDate = await scheduledDay.getAttribute("data-date");
  const scheduleItems = page.locator(".schedule-list .appointment");
  await scheduleItems.first().waitFor();
  const scheduleCount = await scheduleItems.count();
  const firstScheduleText = await scheduleItems.first().innerText();
  await page.screenshot({ path: path.join(__dirname, "counselor-live-schedule.png"), fullPage: true });
  await scheduleItems.first().click();
  await page.locator(".client-appointment-panel").waitFor();
  const detailScheduleText = await page.locator(".client-appointment-panel").innerText();
  await page.screenshot({ path: path.join(__dirname, "client-schedule-detail.png"), fullPage: true });

  await page.goto(`${baseUrl}/counselor/copilot`, { waitUntil: "networkidle" });
  const clientSelect = page.getByLabel("내담자");
  await clientSelect.selectOption("client-00008");
  await page.getByRole("button", { name: "사전문진으로 1회기 분석", exact: true }).click();
  await page.getByRole("button", { name: "초기상담기록지 초안 생성", exact: true }).waitFor({ timeout: 30000 });
  await page.locator(".session-source-input textarea").fill("내담자는 배우자와의 반복되는 의사소통 갈등을 호소함.");
  await page.getByRole("button", { name: "초기상담기록지 초안 생성", exact: true }).click();
  const genogram = page.locator('[data-genogram-ready="true"]');
  try {
    await genogram.waitFor({ timeout: 30000 });
  } catch (error) {
    console.error("genogram-debug", JSON.stringify({ formErrors: await page.locator(".form-error").allTextContents(), errors, url: page.url() }, null, 2));
    await page.screenshot({ path: path.join(__dirname, "genogram-debug.png"), fullPage: true });
    throw error;
  }
  const svg = genogram.locator("svg");
  const svgBox = await svg.boundingBox();
  const sourceText = await page.getByLabel("가족관계 참고사항").inputValue();
  const nodeCount = await svg.locator(".genogram-node-shape").count();
  await genogram.scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(__dirname, "official-genogram-rendered.png"), fullPage: true });

  await page.getByLabel("가족관계 참고사항").fill("");
  const fallbackNodeCount = await svg.locator(".genogram-node-shape").count();
  const rootLabel = await svg.locator(".genogram-person-label").first().textContent();

  const result = { browserTodayKey, initiallySelectedDate, defaultScheduleCount, selectedScheduledDate, scheduleCount, firstScheduleText, detailScheduleText, sourceText, nodeCount, fallbackNodeCount, rootLabel, svgBox, errors };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (initiallySelectedDate !== browserTodayKey || scheduleCount < 1 || !detailScheduleText.includes("다음 상담 일정") || !sourceText || nodeCount < 1 || fallbackNodeCount !== 1 || !rootLabel || !svgBox || svgBox.width < 200 || svgBox.height < 150 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
