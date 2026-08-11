const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const baseUrl = process.env.VISUAL_BASE_URL || "http://127.0.0.1:3000";
  const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("CNS-SEO-00001");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor");
  await page.goto(`${baseUrl}/counselor/clients`, { waitUntil: "networkidle" });
  await page.getByText("총 14명 · 페이지당 10명", { exact: true }).waitFor();
  const rows = await page.locator(".data-table tbody tr").count();
  const pagination = await page.locator(".client-pagination").innerText();
  await page.screenshot({ path: path.join(__dirname, "linked-client-list.png"), fullPage: true });

  await page.locator(".data-table tbody tr").first().getByText("상세 보기 →", { exact: true }).click();
  await page.getByText("사전문진 원 응답", { exact: true }).waitFor();
  const sections = await page.locator(".questionnaire-sections details").count();
  const responseRows = await page.locator(".questionnaire-sections details").first().locator("tbody tr").count();
  await page.screenshot({ path: path.join(__dirname, "linked-client-detail.png"), fullPage: true });

  console.log(JSON.stringify({ rows, pagination, sections, firstSectionResponses: responseRows, errors }, null, 2));
  await browser.close();
  if (rows !== 10 || !pagination.includes("1 / 2") || sections !== 4 || responseRows !== 18 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
