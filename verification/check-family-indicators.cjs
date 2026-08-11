const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("admin");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/admin/dashboard");
  await page.locator(".family-indicator-panel").waitFor();

  const readIndicators = () => page.locator(".family-indicator-row").evaluateAll(rows => rows.map(row => ({
    label: row.querySelector(".family-indicator-name b")?.textContent?.trim(),
    score: row.querySelector(".family-indicator-score")?.textContent?.trim(),
    status: row.querySelector(".family-indicator-status")?.textContent?.trim(),
  })));

  const national = await readIndicators();
  const counselorTableCount = await page.locator(".counselor-dashboard-table").count();

  const regionLabel = page.locator(".korea-map-label").first();
  const regionName = ((await regionLabel.locator(".region-name").textContent()) ?? "").trim();
  await regionLabel.click();
  await page.waitForFunction(name => {
    const heading = document.querySelector(".family-indicator-heading small")?.textContent ?? "";
    return heading.includes(name);
  }, regionName);
  const region = await readIndicators();

  const centerButton = page.locator(".center-browser-list button").first();
  const centerName = (await centerButton.locator("span:first-child b").innerText()).trim();
  await centerButton.click();
  await page.waitForFunction(name => {
    const heading = document.querySelector(".family-indicator-heading small")?.textContent ?? "";
    return heading.includes(name);
  }, centerName);
  const center = await readIndicators();

  await page.screenshot({ path: path.join(__dirname, "dashboard-family-indicators.png"), fullPage: true });
  const result = { national, regionName, region, centerName, center, counselorTableCount, errors };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();

  const required = ["가족기능", "가족위기성", "가족관계 회복력", "위기대응 자원", "지원·연계 수요"];
  const labels = national.map(item => item.label);
  const scoresChanged = JSON.stringify(national.map(item => item.score)) !== JSON.stringify(region.map(item => item.score))
    && JSON.stringify(region.map(item => item.score)) !== JSON.stringify(center.map(item => item.score));
  if (!required.every(label => labels.includes(label)) || national.length !== 5 || counselorTableCount || !scoresChanged || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
