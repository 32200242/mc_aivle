const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--autoplay-policy=no-user-gesture-required"],
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor", { timeout: 15000 });
  await page.goto("http://127.0.0.1:3000/training", { waitUntil: "networkidle" });
  await page.locator(".stt-button").waitFor();
  await page.getByRole("button", { name: "전송", exact: true }).click();
  await page.locator(".response-box").getByText("제 마음은 전혀 전달되지 않은 것 같아서", { exact: false }).waitFor({ timeout: 20000 });
  const video = page.locator(".avatar-video");
  await video.waitFor({ timeout: 15000 });
  await page.waitForFunction(() => {
    const element = document.querySelector(".avatar-video");
    return element instanceof HTMLVideoElement && element.currentSrc.includes("lee-jieun-counselor-training-final.mp4") && element.readyState >= 2;
  }, { timeout: 15000 });
  const result = await video.evaluate(element => ({
    src: element.currentSrc,
    readyState: element.readyState,
    paused: element.paused,
    muted: element.muted,
  }));
  const response = await page.locator(".response-box").innerText();
  const history = await page.locator(".chat-history .client").count();
  await page.screenshot({ path: path.join(__dirname, "training-restored-first-video.png"), fullPage: true });
  const send = page.getByRole("button", { name: "전송", exact: true });
  await send.waitFor({ state: "visible", timeout: 30000 });
  await page.waitForFunction(() => {
    const button = Array.from(document.querySelectorAll("button")).find(element => element.textContent?.trim() === "전송");
    return button && !button.disabled;
  }, { timeout: 30000 });
  await page.locator(".counselor-input textarea").fill("그 순간 서운함과 지침이 함께 느껴지셨던 것 같아요. 어떤 점이 가장 마음에 남았나요?");
  await send.click();
  await page.waitForFunction(() => document.querySelectorAll(".chat-history .client").length === 2, { timeout: 120000 });
  const secondResponse = await page.locator(".chat-history .client p").last().innerText();
  console.log(JSON.stringify({ result, response, history, secondResponse, errors }, null, 2));
  await browser.close();
  if (!result.src.includes("lee-jieun-counselor-training-final.mp4") || history !== 1 || !secondResponse || secondResponse === response || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
