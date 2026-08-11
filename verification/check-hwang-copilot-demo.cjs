const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle" });
  await page.locator('input[autocomplete="username"]').fill("counselor");
  await page.locator('input[autocomplete="current-password"]').fill("demo");
  await page.getByRole("button", { name: "LOGIN" }).click();
  await page.waitForURL("**/counselor");

  await page.goto("http://127.0.0.1:3000/counselor/clients", { waitUntil: "networkidle" });
  const hwangRow = page.locator("tbody tr").filter({ hasText: "황재훈" });
  const hwangListText = await hwangRow.innerText();
  const menuText = await page.locator(".counselor-sidebar nav").innerText();

  await page.goto("http://127.0.0.1:3000/counselor/clients/client-00013", { waitUntil: "networkidle" });
  const appointmentText = await page.locator(".client-appointment-panel").innerText();
  const tabLabels = await page.locator(".case-hub-tabs button").allTextContents();
  await page.getByRole("button", { name: "문진·척도" }).click();
  const assessmentVisible = await page.getByRole("heading", { name: "사전문진 핵심 요약" }).isVisible();
  await page.screenshot({ path: path.join(__dirname, "hwang-assessment-insight-summary.png"), fullPage: true });
  await page.getByRole("button", { name: "회기 기록" }).click();
  const terminationDocumentText = await page.locator(".closing-report-gate").innerText();
  await page.getByRole("button", { name: "사례 개요" }).click();
  const copilotHref = await page.getByRole("link", { name: /2회기 상담 코파일럿 열기/ }).getAttribute("href");

  await page.goto(`http://127.0.0.1:3000${copilotHref}`, { waitUntil: "networkidle" });
  const pageTitle = await page.locator(".counselor-topbar h1").innerText();
  const stepLabels = await page.locator(".copilot-stepper button b").allTextContents();
  const initialImageCount = await page.locator(".ocr-document-previews img").count();
  await page.screenshot({ path: path.join(__dirname, "hwang-copilot-step-1.png"), fullPage: true });

  await page.getByRole("button", { name: /선택 완료 · 분석으로/ }).click();
  await page.getByRole("button", { name: "2회기 분석 실행" }).click();
  await page.locator(".module-analysis-panel").waitFor();
  const moduleCount = await page.locator(".module-analysis-grid > article").count();
  await page.getByRole("button", { name: /다음: 상담자료 입력/ }).click();

  const step3 = await page.locator(".copilot-stepper button.active b").innerText();
  const imageBeforeSoap = await page.locator(".ocr-document-previews img").count();
  const soapFieldsBeforeToggle = await page.locator(".soap-field-row").count();
  const directNextDisabled = await page.getByRole("button", { name: /다음: 기록 작성/ }).isDisabled();
  await page.screenshot({ path: path.join(__dirname, "hwang-copilot-step-3-direct-input.png"), fullPage: true });

  await page.locator(".optional-soap-toggle input").check();
  const imageBeforeUpload = await page.locator(".ocr-document-previews img").count();
  const directSoapFields = await page.locator(".soap-field-row").count();
  const directSoapNextDisabled = await page.getByRole("button", { name: /다음: 기록 작성/ }).isDisabled();
  const uploadPath = path.resolve(__dirname, "../frontend/public/demo/hwang-jaehoon-couple-soap-handwritten-0829.png");
  await page.locator(".soap-file-button input").setInputFiles(uploadPath);
  const uploadedImage = page.locator('img[alt="hwang-jaehoon-couple-soap-handwritten-0829.png 원본 미리보기"]');
  await uploadedImage.waitFor();
  const uploadedImageLoaded = await uploadedImage.evaluate(async node => { if (!node.complete) await new Promise(resolve => node.addEventListener("load", resolve, { once: true })); return node.naturalWidth > 0 && node.src.startsWith("blob:"); });
  const selectedFilenameVisible = await page.getByText(/hwang-jaehoon-couple-soap-handwritten-0829.png/).first().isVisible();
  const nextBeforeOCRDisabled = await page.getByRole("button", { name: /다음: 기록 작성/ }).isDisabled();

  await page.getByRole("button", { name: "문서 인식 실행" }).click();
  const firstSoapValue = await page.locator(".soap-field-row textarea").first().inputValue();
  const nextBeforeReviewDisabled = await page.getByRole("button", { name: /다음: 기록 작성/ }).isDisabled();
  await page.locator(".ocr-review-confirm input").check();
  const reviewChecked = await page.locator(".ocr-review-confirm input").isChecked();
  await page.screenshot({ path: path.join(__dirname, "hwang-copilot-step-3-upload-review.png"), fullPage: true });
  await page.getByRole("button", { name: /다음: 기록 작성/ }).click();

  const step4 = await page.locator(".copilot-stepper button.active b").innerText();
  const recordBeforeGenerate = await page.locator(".session-record-form").count();
  const completionBeforeRecordDisabled = await page.getByRole("button", { name: /상담기록지 작성 후 완료/ }).isDisabled();
  await page.getByRole("button", { name: "상담기록지 초안 생성" }).click();
  await page.locator(".session-record-form").waitFor();
  const recordDate = await page.locator('.session-record-form input[type="date"]').inputValue();
  const recordStart = await page.locator('.session-record-form input[type="time"]').first().inputValue();
  const generatedSoapS = await page.getByRole("button", { name: "SOAP 참고자료" }).click().then(() => page.locator(".record-editor textarea").first().inputValue());
  await page.getByRole("button", { name: "상담기록지", exact: true }).click();
  await page.screenshot({ path: path.join(__dirname, "hwang-copilot-step-4-record.png"), fullPage: true });
  const completionLinkVisible = await page.getByRole("link", { name: /상담기록지 작성 완료/ }).isVisible();
  const reportUIAbsent = await page.locator(".report-input-grid,.report-output").count();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("http://127.0.0.1:3000/counselor/copilot?client=client-00013", { waitUntil: "networkidle" });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

  const result = { hwangListText, menuText, appointmentText, tabLabels, assessmentVisible, terminationDocumentText, copilotHref, pageTitle, stepLabels, initialImageCount, moduleCount, step3, imageBeforeSoap, soapFieldsBeforeToggle, directNextDisabled, imageBeforeUpload, directSoapFields, directSoapNextDisabled, uploadedImageLoaded, selectedFilenameVisible, nextBeforeOCRDisabled, nextBeforeReviewDisabled, reviewChecked, firstSoapValue, step4, recordBeforeGenerate, completionBeforeRecordDisabled, recordDate, recordStart, generatedSoapS, completionLinkVisible, reportUIAbsent, mobileOverflow, errors };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();

  if (!hwangListText.includes("상담기록지 작성 필요") || menuText.includes("회기 코파일럿") || !menuText.includes("상담 코파일럿")) process.exit(1);
  if (!appointmentText.includes("2026년 8월 10일") || !appointmentText.includes("09:00 ~ 09:50")) process.exit(1);
  if (tabLabels.join("|") !== "사례 개요|문진·척도|회기 기록" || !assessmentVisible || !terminationDocumentText.includes("상담 종결 후 작성 가능")) process.exit(1);
  if (copilotHref !== "/counselor/copilot?client=client-00013" || pageTitle !== "상담 코파일럿") process.exit(1);
  if (stepLabels.join("|") !== "사례 선택|분석|상담자료 입력|상담기록지 작성" || initialImageCount || moduleCount !== 4) process.exit(1);
  if (step3 !== "상담자료 입력" || imageBeforeSoap || soapFieldsBeforeToggle || directNextDisabled) process.exit(1);
  if (imageBeforeUpload || directSoapFields !== 4 || directSoapNextDisabled || !uploadedImageLoaded || !selectedFilenameVisible || !nextBeforeOCRDisabled || !nextBeforeReviewDisabled || !reviewChecked) process.exit(1);
  if (!firstSoapValue.includes("배우자") || step4 !== "상담기록지 작성" || recordBeforeGenerate || !completionBeforeRecordDisabled) process.exit(1);
  if (recordDate !== "2026-08-10" || recordStart !== "09:00" || !generatedSoapS.includes("배우자")) process.exit(1);
  if (!completionLinkVisible || reportUIAbsent) process.exit(1);
  if (mobileOverflow > 2 || errors.length) process.exit(1);
})().catch(error => { console.error(error); process.exit(1); });
