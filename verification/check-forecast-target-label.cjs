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
  await page.goto("http://127.0.0.1:3000/admin/analytics", { waitUntil: "networkidle" });
  await page.locator(".forecast-chart .service-target-legend").waitFor();

  const geometry = await page.evaluate(() => {
    const line = document.querySelector(".forecast-chart .service-target-line").getBoundingClientRect();
    const legend = document.querySelector(".forecast-chart .service-target-legend").getBoundingClientRect();
    const label = document.querySelector(".forecast-chart .service-target-label").getBoundingClientRect();
    return {
      targetLineY: line.top,
      legendBottom: legend.bottom,
      labelBottom: label.bottom,
      legendGap: line.top - legend.bottom,
      labelGap: line.top - label.bottom,
      backgroundRects: document.querySelectorAll(".forecast-chart .service-target-legend rect").length,
    };
  });

  await page.screenshot({
    path: path.join(__dirname, "forecast-target-label-fixed.png"),
    fullPage: true,
  });
  console.log(JSON.stringify({ geometry, errors }, null, 2));
  await browser.close();

  if (geometry.legendGap < 20 || geometry.labelGap < 20 || geometry.backgroundRects !== 0 || errors.length) process.exit(1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
