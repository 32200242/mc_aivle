const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const outputDir = path.join(__dirname, "institute-pages");
fs.mkdirSync(outputDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  const captures = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  async function capture(route, readySelector, filename) {
    await page.goto(`http://127.0.0.1:3000${route}`, { waitUntil: "networkidle" });
    await page.locator(readySelector).waitFor({ timeout: 20000 });
    const target = path.join(outputDir, filename);
    await page.screenshot({ path: target, fullPage: true });
    captures.push(target);
  }

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("admin");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/admin/dashboard");

  await capture("/admin/dashboard", ".family-indicator-panel", "01-integrated-dashboard.png");
  await capture("/admin/analytics", ".forecast-chart", "02-analysis-and-forecast.png");
  await capture("/admin/reports", ".admin-report-document", "03-report.png");

  console.log(JSON.stringify({ captures, errors }, null, 2));
  await browser.close();
  if (captures.length !== 3 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
