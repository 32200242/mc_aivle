const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const baseUrl = process.env.VISUAL_BASE_URL || "http://127.0.0.1:3000";
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));
  const verification = path.join(__dirname, "verification");
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(verification, "login.png"), fullPage: true });
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page.waitForURL("**/counselor");
  await page.goto(`${baseUrl}/training`, { waitUntil: "networkidle" });
  await page.locator(".avatar-status").waitFor();
  await page.waitForTimeout(3500);
  const initialStatus = await page.locator(".avatar-status").innerText();
  await page.screenshot({ path: path.join(verification, "training-initial.png"), fullPage: true });
  await page.locator(".counselor-input textarea").fill("남편과 갈등할 때 어떤 감정이 가장 먼저 드나요?");
  await page.getByRole("button", { name: "전송" }).click();
  await page.getByText("팔짱 끼기", { exact: true }).first().waitFor({ timeout: 15000 });
  await page.waitForTimeout(1200);
  const response = await page.locator(".response-box").innerText();
  const cueCount = await page.locator(".cue-list > div").count();
  const canvasCount = await page.locator(".avatar-canvas canvas").count();
  await page.screenshot({ path: path.join(verification, "training-response.png"), fullPage: true });
  await page.goto(`${baseUrl}/counselor/copilot`, { waitUntil: "networkidle" });
  await page.locator(".case-identity-card").waitFor();
  const loadedCaseCode = await page.locator(".case-identity-card small").innerText();
  const assessmentCount = await page.locator(".assessment-strip article").count();
  await page.getByRole("button", { name: "선택 사례 전체 데이터로 AI 분석" }).click();
  await page.getByText("SOAP 기록 초안", { exact: true }).waitFor({ timeout: 90000 });
  const copilotSummary = await page.locator(".analysis-summary").innerText();
  const brandLogoCount = await page.locator('img[src="/brand/family-center-logo.png"]').count();
  await page.screenshot({ path: path.join(verification, "copilot-response.png"), fullPage: true });
  console.log(JSON.stringify({ initialStatus, response, cueCount, canvasCount, loadedCaseCode, assessmentCount, copilotSummary, brandLogoCount, errors }, null, 2));
  await browser.close();
  if (!response.includes("방어적") || cueCount < 2 || canvasCount !== 1 || !loadedCaseCode.includes("FC-2026") || assessmentCount !== 4 || !copilotSummary || brandLogoCount < 1 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
