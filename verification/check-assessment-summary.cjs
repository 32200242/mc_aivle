const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const baseUrl = process.env.FRONTEND_URL || "http://127.0.0.1:3000";
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1720, height: 1050 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor", { timeout: 15000 });

  await page.goto(`${baseUrl}/counselor/clients/client-001`, { waitUntil: "networkidle" });
  const summary = page.locator(".assessment-insight-grid").first();
  await summary.waitFor({ timeout: 15000 });
  const cards = summary.locator(":scope > article");
  const cardCount = await cards.count();
  const titles = await cards.locator("h3").allTextContents();
  const evidence = await cards.locator("em").allTextContents();
  await page.screenshot({ path: path.join(__dirname, "assessment-summary-official-scoring.png"), fullPage: true });

  await page.getByRole("button", { name: "문진·척도" }).click();
  const stressSection = page.locator(".questionnaire-sections details").filter({ hasText: "FSTRESS" });
  await stressSection.locator("summary").click();
  const stressRows = stressSection.locator("tbody tr");
  const rowCount = await stressRows.count();
  const responseLabels = await stressRows.locator("td:last-child span").allTextContents();
  const invalidLabels = responseLabels.filter(label => !/^경험 (없음|있음 · 부담 (매우 낮음|낮음|보통|높음|매우 높음))$/.test(label));

  const result = { cardCount, titles, evidence, stressRows: rowCount, invalidLabels, errors };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();

  if (
    cardCount !== 4 ||
    titles[0] !== "가족관계 문제징후" ||
    titles[1] !== "생활사건 경험과 부담" ||
    !/^총점 \d+\/90 · 확인 기준 54$/.test(evidence[0]) ||
    !/^경험빈도 \d+\/45 · 부담 합계 \d+\/225$/.test(evidence[1]) ||
    rowCount !== 45 ||
    invalidLabels.length ||
    errors.length
  ) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
