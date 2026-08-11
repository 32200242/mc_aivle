const fs = require("fs");
const path = require("path");
const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const BASE_URL = process.env.FRONTEND_URL || "http://127.0.0.1:3000";
const OUTPUT_DIR = path.join(__dirname, "all-tabs-20260811");

async function login(page, username) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill(username);
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL(username === "admin" ? "**/admin/dashboard" : "**/counselor", { timeout: 20000 });
}

async function expandAll(page) {
  await page.locator("details").evaluateAll(elements => elements.forEach(element => { element.open = true; }));
  await page.waitForTimeout(350);
}

async function capture(page, filename, readySelector) {
  if (readySelector) await page.locator(readySelector).first().waitFor({ timeout: 30000 });
  await expandAll(page);
  await page.addStyleTag({ content: `
    *,*::before,*::after { animation-duration:0s !important; transition-duration:0s !important; caret-color:transparent !important; }
    nextjs-portal { display:none !important; }
  ` });
  await page.waitForTimeout(450);
  const output = path.join(OUTPUT_DIR, filename);
  await page.screenshot({ path: output, fullPage: true });
  return output;
}

async function gotoAndCapture(page, route, filename, readySelector) {
  await page.goto(`${BASE_URL}${route}`, { waitUntil: "networkidle" });
  return capture(page, filename, readySelector);
}

(async () => {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const context = await browser.newContext({ viewport: { width: 1720, height: 1050 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  const outputs = [];

  await login(page, "admin");
  outputs.push(await gotoAndCapture(page, "/admin/dashboard", "01-kihf-dashboard.png", ".dashboard-kpis"));
    outputs.push(await gotoAndCapture(page, "/admin/analytics", "02-kihf-analytics.png", ".analytics-toolbar"));
  outputs.push(await gotoAndCapture(page, "/admin/reports", "03-kihf-reports.png", ".admin-report-document"));

  await page.evaluate(() => localStorage.clear());
  await login(page, "counselor");
  outputs.push(await gotoAndCapture(page, "/counselor", "04-family-center-main.png", ".counselor-home-grid"));
  outputs.push(await gotoAndCapture(page, "/counselor/clients", "05-family-center-clients.png", ".data-table"));

  await page.goto(`${BASE_URL}/counselor/clients/client-00013`, { waitUntil: "networkidle" });
  await page.locator(".case-hub-tabs").waitFor();
  outputs.push(await capture(page, "06-client-overview.png", ".case-hub-tabs"));
  await page.getByRole("button", { name: "문진·척도", exact: true }).click();
  outputs.push(await capture(page, "07-client-assessments-expanded.png", ".questionnaire-sections"));
  await page.getByRole("button", { name: "회기 기록", exact: true }).click();
  outputs.push(await capture(page, "08-client-records.png", ".case-hub-tabs"));

  await page.goto(`${BASE_URL}/counselor/copilot?client=client-00013`, { waitUntil: "networkidle" });
  await page.locator(".copilot-stepper").waitFor();
  outputs.push(await capture(page, "09-copilot-step1-case.png", ".case-selector-grid"));
  await page.getByRole("button", { name: /선택 완료 · 분석으로/ }).click();
  await page.getByRole("button", { name: /2회기 분석 실행/ }).click();
  await page.locator(".module-analysis-panel").waitFor();
  outputs.push(await capture(page, "10-copilot-step2-analysis-expanded.png", ".module-analysis-panel"));
  await page.getByRole("button", { name: /다음: 상담자료 입력/ }).click();
  await page.locator(".counseling-source-stage").waitFor();
  await page.locator(".optional-soap-toggle input").check();
  outputs.push(await capture(page, "11-copilot-step3-source-expanded.png", ".optional-soap-workspace"));
  await page.getByRole("button", { name: /다음: 기록 작성/ }).click();
  await page.getByRole("button", { name: /상담기록지 초안 생성/ }).click();
  await page.getByText("편집 가능한 공식 기록", { exact: true }).waitFor({ timeout: 30000 });
  outputs.push(await capture(page, "12-copilot-step4-session-record.png", ".official-record-form"));
  await page.getByRole("button", { name: "SOAP 참고자료", exact: true }).click();
  outputs.push(await capture(page, "13-copilot-step4-soap.png", ".record-editor"));
  await page.getByRole("button", { name: "근거·확인사항", exact: true }).click();
  outputs.push(await capture(page, "14-copilot-step4-evidence.png", ".evidence-grid"));

  outputs.push(await gotoAndCapture(page, "/training", "15-persona-training.png", ".training-layout"));

  fs.writeFileSync(path.join(OUTPUT_DIR, "manifest.json"), JSON.stringify({ outputs, errors }, null, 2));
  console.log(JSON.stringify({ outputDir: OUTPUT_DIR, count: outputs.length, errors }, null, 2));
  await browser.close();
  if (errors.length) process.exit(1);
})().catch(error => {
  console.error(error);
  process.exit(1);
});
