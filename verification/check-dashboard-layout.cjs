const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("admin");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/admin/dashboard");
  await page.locator(".dashboard-map-grid").waitFor();

  const layout = await page.evaluate(() => {
    const mapPanel = document.querySelector(".regional-map-panel").getBoundingClientRect();
    const centerPanel = document.querySelector(".center-browser-panel").getBoundingClientRect();
    const centerList = document.querySelector(".center-browser-list").getBoundingClientRect();
    return {
      mapPanel: { width: mapPanel.width, height: mapPanel.height, bottom: mapPanel.bottom },
      centerPanel: { width: centerPanel.width, height: centerPanel.height, bottom: centerPanel.bottom },
      centerList: { height: centerList.height, bottom: centerList.bottom },
      listBottomInset: centerPanel.bottom - centerList.bottom,
    };
  });

  await page.screenshot({
    path: path.join(__dirname, "dashboard-map-panels-aligned.png"),
    fullPage: true,
  });
  console.log(JSON.stringify({ layout, errors }, null, 2));
  await browser.close();

  const widthDelta = Math.abs(layout.mapPanel.width - layout.centerPanel.width);
  const heightDelta = Math.abs(layout.mapPanel.height - layout.centerPanel.height);
  if (widthDelta > 1 || heightDelta > 1 || layout.listBottomInset > 22 || errors.length) process.exit(1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
