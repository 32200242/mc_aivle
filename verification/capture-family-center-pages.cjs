const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const outputDir = path.join(__dirname, "family-center-pages");
fs.mkdirSync(outputDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--autoplay-policy=no-user-gesture-required"],
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  const captures = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  async function capture(filename) {
    const target = path.join(outputDir, filename);
    await page.screenshot({ path: target, fullPage: true });
    captures.push(target);
  }

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await capture("01-login.png");
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor");
  await page.waitForLoadState("networkidle");
  await capture("02-counselor-main.png");

  await page.goto("http://127.0.0.1:3000/counselor/clients", { waitUntil: "networkidle" });
  await page.locator("tbody tr").filter({ hasText: "황재훈" }).waitFor();
  await capture("03-client-list.png");

  await page.goto("http://127.0.0.1:3000/counselor/clients/client-00013", { waitUntil: "networkidle" });
  await page.locator(".case-hub-tabs").waitFor();
  await capture("04-client-overview.png");
  await page.getByRole("button", { name: "문진·척도" }).click();
  await capture("05-client-assessments.png");
  await page.getByRole("button", { name: "회기 기록" }).click();
  await capture("06-client-records.png");

  await page.goto("http://127.0.0.1:3000/counselor/copilot?client=client-00013", { waitUntil: "networkidle" });
  await page.locator(".copilot-stepper").waitFor();
  await capture("07-copilot-1-case.png");
  await page.getByRole("button", { name: /선택 완료 · 분석으로/ }).click();
  await page.getByRole("button", { name: "2회기 분석 실행" }).click();
  await page.locator(".module-analysis-panel").waitFor();
  await capture("08-copilot-2-analysis-complete.png");
  await page.getByRole("button", { name: /다음: 상담자료 입력/ }).click();
  await capture("09-copilot-3-direct-memo.png");
  await page.locator(".optional-soap-toggle input").check();
  await page.locator(".soap-direct-entry").waitFor();
  await capture("10-copilot-3-soap-direct-input.png");

  const uploadPath = path.resolve(__dirname, "../frontend/public/demo/hwang-jaehoon-couple-soap-handwritten-0829.png");
  await page.locator(".soap-file-button input").setInputFiles(uploadPath);
  await page.locator(".soap-review-layout img").waitFor();
  await page.getByRole("button", { name: "문서 인식 실행" }).click();
  await page.locator(".ocr-review-confirm input").check();
  await capture("11-copilot-3-soap-upload-ocr-reviewed.png");
  await page.getByRole("button", { name: /다음: 기록 작성/ }).click();
  await page.getByRole("button", { name: "상담기록지 초안 생성" }).click();
  await page.locator(".session-record-form").waitFor();
  await capture("12-copilot-4-record-complete.png");

  await page.goto("http://127.0.0.1:3000/training", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "전송", exact: true }).waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const button = Array.from(document.querySelectorAll("button")).find(item => item.textContent?.trim() === "전송");
    return button && !button.disabled;
  }, { timeout: 15000 });
  await capture("13-training-ready.png");
  await page.getByRole("button", { name: "전송", exact: true }).click();
  await page.locator(".response-box").getByText("제 마음은 전혀 전달되지 않은 것 같아서", { exact: false }).waitFor({ timeout: 20000 });
  await page.waitForFunction(() => {
    const video = document.querySelector(".avatar-video");
    return video instanceof HTMLVideoElement && video.readyState >= 2 && !video.paused;
  }, { timeout: 15000 });
  await capture("14-training-first-response-video.png");

  console.log(JSON.stringify({ outputDir, captures, errors }, null, 2));
  await browser.close();
  if (captures.length !== 14 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
