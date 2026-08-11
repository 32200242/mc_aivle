const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1720, height: 1050 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor", { timeout: 15000 });
  await page.goto("http://127.0.0.1:3000/counselor/clients", { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "내담자 목록", exact: true }).waitFor();

  const pageText = await page.locator("body").innerText();
  const appointmentTexts = await page.locator(".data-table tbody tr td:nth-child(6)").allTextContents();
  const appointmentDates = appointmentTexts.map(value => {
    const match = /(\d{2})\.\s*(\d{2})\./.exec(value);
    return match ? `2026-${match[1]}-${match[2]}` : null;
  });
  const staleDates = appointmentDates.filter(value => value && value < "2026-08-10");
  await page.screenshot({ path: path.join(__dirname, "client-list-realistic-schedule.png"), fullPage: true });

  const result = {
    appointmentTexts,
    appointmentDates,
    staleDates,
    hasAssignmentCopy: pageText.includes("로그인한 상담사에게 배정된") || pageText.includes("배정 데이터 연동"),
    errors,
  };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (result.hasAssignmentCopy || staleDates.length || appointmentTexts.length !== 10 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
