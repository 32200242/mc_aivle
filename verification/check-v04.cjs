const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("http://127.0.0.1:3002/login", { waitUntil: "networkidle" });
  await page.waitForTimeout(1800);
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page.waitForTimeout(2500);
  if (!page.url().endsWith("/counselor")) {
    console.log("login-url", page.url(), "login-error", await page.locator(".form-error").allTextContents(), "console-errors", errors);
  }
  await page.waitForURL("**/counselor", { timeout: 10000 });

  await page.goto("http://127.0.0.1:3002/counselor/copilot", { waitUntil: "networkidle" });
  await page.getByText("OCR 기록 통합", { exact: true }).waitFor();
  await page.getByLabel("OCR 정제 텍스트").fill("수기 기록: 배우자와 대화할 때 불안과 긴장을 호소함");
  await page.getByRole("button", { name: "초기상담기록지·상담기록지·SOAP 통합 초안 생성" }).click();
  await page.getByText("편집 가능한 통합 기록", { exact: true }).waitFor();
  await page.getByRole("button", { name: "SOAP 일지", exact: true }).click();
  const soapEditors = await page.locator(".record-editor textarea").count();
  await page.getByRole("button", { name: "회기·종결 보고서 생성" }).click();
  await page.getByLabel("회기 요약 초안").waitFor();
  const reportText = await page.getByLabel("회기 요약 초안").inputValue();
  await page.screenshot({ path: path.join(__dirname, "copilot-records-report.png"), fullPage: true });

  await page.goto("http://127.0.0.1:3002/training", { waitUntil: "networkidle" });
  await page.locator(".stt-button").waitFor();
  const sttText = await page.locator(".stt-button").innerText();
  const sttHint = await page.locator(".stt-hint").innerText();
  await page.screenshot({ path: path.join(__dirname, "training-stt.png"), fullPage: true });

  console.log(JSON.stringify({ soapEditors, reportLength: reportText.length, sttText, sttHint, errors }, null, 2));
  await browser.close();
  if (soapEditors !== 4 || reportText.length < 30 || !sttText.includes("STT") || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
