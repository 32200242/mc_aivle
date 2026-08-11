const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.locator('input[autocomplete="username"]').fill("counselor");
  await page.locator('input[autocomplete="current-password"]').fill("demo");
  await page.getByRole("button", { name: "LOGIN" }).click();
  await page.waitForURL("**/counselor");
  await page.goto("http://127.0.0.1:3000/counselor/clients/client-00007", { waitUntil: "networkidle" });
  await page.locator(".client-header").waitFor();

  const header = await page.locator(".client-header").innerText();
  const appointment = await page.locator(".client-appointment-panel").innerText();
  const copilotButton = page.getByRole("link", { name: "코파일럿에서 분석하기 →" });
  const copilotButtonColor = await copilotButton.evaluate((element) => getComputedStyle(element).color);
  const assessmentGrid = page.locator(".assessment-summary-grid.compact");
  const assessmentColumns = await assessmentGrid.evaluate((element) => getComputedStyle(element).gridTemplateColumns);
  const overviewPanelHeight = await page.locator(".two-col .panel").first().evaluate((element) => element.getBoundingClientRect().height);
  const body = await page.locator("body").innerText();
  await page.screenshot({
    path: path.join(__dirname, "client-start-schedule-consistent.png"),
    fullPage: true,
  });

  console.log(JSON.stringify({ header, appointment, copilotButtonColor, assessmentColumns, overviewPanelHeight, hasEmptyRecordState: body.includes("아직 확정된 상담 기록이 없습니다."), errors }, null, 2));
  await browser.close();

  if (!header.includes("2026.08.15 시작 예정")) process.exit(1);
  if (header.includes("2026.03.07")) process.exit(1);
  if (!appointment.includes("2026년 8월 15일") || !appointment.includes("1회기 예정")) process.exit(1);
  if (copilotButtonColor !== "rgb(255, 255, 255)") process.exit(1);
  if (assessmentColumns.trim().split(/\s+/).length !== 2 || overviewPanelHeight > 520) process.exit(1);
  if (!body.includes("아직 확정된 상담 기록이 없습니다.") || body.includes("4회기 확정 기록")) process.exit(1);
  if (errors.length) process.exit(1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
