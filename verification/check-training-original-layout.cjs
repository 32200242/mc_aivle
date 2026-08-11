const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--autoplay-policy=no-user-gesture-required"],
  });
  const page = await browser.newPage({ viewport: { width: 1720, height: 1200 } });
  const errors = [];
  let fixedVideoRequests = 0;
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (request.url().includes("lee-jieun-counselor-training-final.mp4")) fixedVideoRequests += 1;
  });

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.getByLabel("아이디").fill("counselor");
  await page.getByLabel("비밀번호").fill("demo");
  await page.getByRole("button", { name: "LOGIN", exact: true }).click();
  await page.waitForURL("**/counselor", { timeout: 15000 });
  await page.goto("http://127.0.0.1:3000/training", { waitUntil: "networkidle" });

  const personaSelect = page.getByLabel("내담자 페르소나");
  await personaSelect.waitFor();
  await page.getByRole("button", { name: "전송", exact: true }).waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const button = Array.from(document.querySelectorAll("button")).find(item => item.textContent?.trim() === "전송");
    return button && !button.disabled;
  }, { timeout: 15000 });
  const initial = {
    persona: await personaSelect.inputValue(),
    scenario: await page.locator(".scenario-copy h2").innerText(),
    firstComplaint: await page.locator(".scenario-copy blockquote").innerText(),
    photoSrc: await page.locator(".avatar-photo").getAttribute("src"),
    personaText: await page.locator(".persona-overlay").innerText(),
    warningCount: await page.locator(".ai-mode-warning").count(),
    preloadedVideo: await page.locator(".avatar-video").evaluate(element => ({
      src: element.currentSrc,
      readyState: element.readyState,
      networkState: element.networkState,
    })),
    duplicateEmotionTags: await page.locator(".emotion-tags").count(),
  };
  await page.screenshot({ path: path.join(__dirname, "training-original-layout-restored.png"), fullPage: true });

  await page.getByRole("button", { name: "전송", exact: true }).click();
  await page.locator(".response-box").getByText("제 마음은 전혀 전달되지 않은 것 같아서", { exact: false }).waitFor({ timeout: 20000 });
  await page.waitForFunction(() => {
    const video = document.querySelector(".avatar-video");
    return video instanceof HTMLVideoElement &&
      video.currentSrc.includes("lee-jieun-counselor-training-final.mp4") &&
      video.readyState >= 2 && !video.paused;
  }, { timeout: 15000 });
  const video = await page.locator(".avatar-video").evaluate(element => ({
    src: element.currentSrc,
    paused: element.paused,
    muted: element.muted,
    readyState: element.readyState,
  }));
  const requestsAfterFirstPlay = fixedVideoRequests;
  await page.waitForTimeout(900);
  const timeBeforeReplay = await page.locator(".avatar-video").evaluate(element => element.currentTime);
  await page.getByRole("button", { name: "최근 응답 다시 듣기", exact: true }).click();
  await page.waitForFunction(() => {
    const element = document.querySelector(".avatar-video");
    return element instanceof HTMLVideoElement && !element.paused && element.currentTime < 0.7;
  });
  await page.waitForTimeout(200);
  const replay = await page.locator(".avatar-video").evaluate(element => ({
    currentTime: element.currentTime,
    paused: element.paused,
    readyState: element.readyState,
  }));
  await page.screenshot({ path: path.join(__dirname, "training-first-response-mp4.png"), fullPage: true });

  const result = { initial, video, replay, timeBeforeReplay, requestsAfterFirstPlay, requestsAfterReplay: fixedVideoRequests, errors };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (
    initial.persona !== "lee-jieun" ||
    !initial.photoSrc?.includes("/personas/lee-jieun/neutral.png") ||
    !initial.personaText.includes("이지은") ||
    initial.warningCount !== 0 ||
    !initial.preloadedVideo.src.includes("lee-jieun-counselor-training-final.mp4") ||
    initial.preloadedVideo.readyState < 3 ||
    initial.duplicateEmotionTags !== 0 ||
    !video.src.includes("lee-jieun-counselor-training-final.mp4") ||
    video.paused || video.muted ||
    timeBeforeReplay < .5 || replay.paused || replay.readyState < 3 ||
    fixedVideoRequests !== requestsAfterFirstPlay || errors.length
  ) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
