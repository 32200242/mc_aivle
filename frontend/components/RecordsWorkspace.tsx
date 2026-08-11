"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { finalizeSessionRecord, generateIntegratedRecords, getOCRStatus, runOCR } from "@/lib/api";
import type { IntegratedRecords, OCRResult, OCRStatus } from "@/lib/types";
import { Panel, Tag } from "@/components/UI";
import GenogramDiagram from "@/components/GenogramDiagram";
import {
  HWANG_DEMO_CLIENT_ID,
  HWANG_EXISTING_SUMMARY,
  HWANG_OCR_RESULT,
  HWANG_OCR_REVIEW_NOTE,
  HWANG_OCR_STATUS,
  HWANG_OCR_TEXT,
  HWANG_SESSION_TEXT,
  buildHwangRecords,
} from "@/data/hwangCopilotDemo";


const initialFields = ["내담자 호소문제(주제)", "상담목표(내담자와 합의된 목표)", "상담계획", "상담내용", "가계도"];
const sessionFields = ["상담주제 1순위", "상담주제 2순위", "상담주제 3순위", "당회기 상담목표", "상담내용(상담개입)", "다음 회기 계획", "연계기관"];
const counselingMethods = ["면접상담", "사이버상담", "방문상담", "전화상담"];
const counselingTypes = ["이혼전후상담", "부부상담", "부모자녀상담", "그 외 가족상담", "개인상담"];
const soapFields = ["S", "O", "A", "P"] as const;
const officialRecordFieldMaxLength = 300;
type RecordTab = "initial" | "session" | "soap" | "evidence";
type SoapDraft = Record<(typeof soapFields)[number], string>;
const emptySoapDraft: SoapDraft = { S: "", O: "", A: "", P: "" };


export default function RecordsWorkspace({ activeStep, onStepChange, clientId, sessionNumber, sessionDate, hasNextSession, sourceText, goal, note, sourceLabel, onFinalized }: { activeStep: number; onStepChange: (step: number) => void; clientId: string; sessionNumber: number; sessionDate: string; hasNextSession: boolean; sourceText: string; goal: string; note: string; sourceLabel: string; onFinalized?: (nextSessionNumber: number | null) => void }) {
  const preparedCase = clientId === HWANG_DEMO_CLIENT_ID && sessionNumber === 2;
  const [ocrStatus, setOCRStatus] = useState<OCRStatus | null>(preparedCase ? HWANG_OCR_STATUS : null);
  const [files, setFiles] = useState<File[]>([]);
  const [formHint, setFormHint] = useState(preparedCase ? "SOAP 일지" : "자동 판별");
  const [preprocessMode, setPreprocessMode] = useState("원본");
  const [useGpu] = useState(true);
  const [ocrResult, setOCRResult] = useState<OCRResult | null>(null);
  const [ocrText, setOCRText] = useState("");
  const [soapDraft, setSoapDraft] = useState<SoapDraft>(emptySoapDraft);
  const [ocrReviewed, setOCRReviewed] = useState(false);
  const [manualCorrection, setManualCorrection] = useState("");
  const [existingSummary, setExistingSummary] = useState(preparedCase ? HWANG_EXISTING_SUMMARY : "");
  const [sessionText, setSessionText] = useState(preparedCase ? HWANG_SESSION_TEXT : sourceText);
  const [records, setRecords] = useState<IntegratedRecords | null>(null);
  const [generatedOCRSource, setGeneratedOCRSource] = useState<string | null>(null);
  const [recordTab, setRecordTab] = useState<RecordTab>(sessionNumber === 1 ? "initial" : "session");
  const [ocrBusy, setOCRBusy] = useState(false);
  const [recordBusy, setRecordBusy] = useState(false);
  const [finalizeBusy, setFinalizeBusy] = useState(false);
  const [includeSoap, setIncludeSoap] = useState(false);
  const [serviceDate, setServiceDate] = useState(sessionDate);
  const [finalized, setFinalized] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (preparedCase) {
      setOCRStatus(HWANG_OCR_STATUS);
      return;
    }
    getOCRStatus().then(setOCRStatus).catch(() => undefined);
  }, [preparedCase]);

  const filePreviews = useMemo(() => files.map(file => ({
    name: file.name,
    type: file.type,
    url: URL.createObjectURL(file),
  })), [files]);

  useEffect(() => () => filePreviews.forEach(file => URL.revokeObjectURL(file.url)), [filePreviews]);

  async function extractOCR() {
    if (preparedCase) {
      if (!files.length) return setError("이미지 또는 PDF를 먼저 선택하세요.");
      setOCRBusy(true);
      setOCRResult(HWANG_OCR_RESULT);
      setOCRText(HWANG_OCR_TEXT);
      setSoapDraft(parseSoapText(HWANG_OCR_TEXT));
      setManualCorrection(HWANG_OCR_REVIEW_NOTE);
      setOCRReviewed(false);
      setError("");
      setOCRBusy(false);
      return;
    }
    if (!files.length) return setError("이미지 또는 PDF를 먼저 선택하세요.");
    setOCRBusy(true); setError("");
    try {
      const result = await runOCR(files, preprocessMode, formHint, useGpu);
      setOCRResult(result);
      setOCRText(result.clean_text);
      setSoapDraft(parseSoapText(result.clean_text));
      setOCRReviewed(false);
    } catch {
      setError("문서 인식 처리에 실패했습니다. 연결 상태를 확인해 주세요.");
    } finally { setOCRBusy(false); }
  }

  async function createRecords() {
    const soapText = includeSoap ? soapFields.filter(field => soapDraft[field].trim()).map(field => `${field}: ${soapDraft[field].trim()}`).join("\n") : "";
    if (!sessionText.trim() && !soapText && !note.trim()) return setError("이번 상담 메모·음성 입력 텍스트 또는 SOAP 직접 입력 내용이 필요합니다.");
    if (files.length && ocrResult && !ocrReviewed) return setError("업로드 원본을 대조하고 누락·오류를 수정한 뒤 ‘원본 검수 완료’를 선택하세요.");
    setRecordBusy(true); setError("");
    try {
      const preparedRecords = buildHwangRecords(serviceDate);
      const created = preparedCase ? { ...preparedRecords, soap: includeSoap ? { ...soapDraft } : {} } : await generateIntegratedRecords({
        record_type: sessionNumber === 1 ? "initial_intake" : "session_record", include_soap: includeSoap,
        client_id: clientId, session_number: sessionNumber,
        transcript: sessionText, session_goal: goal, counselor_note: note, ocr_text: soapText,
        manual_correction: manualCorrection,
        ocr_reviewed: ocrReviewed,
        ocr_review_note: manualCorrection || "업로드 원본과 OCR 전사문 대조 완료",
        ocr_review_flags: ocrResult?.review_reasons ?? [],
        existing_summary: existingSummary, form_hint: formHint,
      });
      setRecords(created);
      setGeneratedOCRSource(`${soapText}\u0000${manualCorrection}`);
      const generatedDate = (sessionNumber === 1 ? created.initial_intake : created.session_record)["상담일자"];
      if (generatedDate) setServiceDate(generatedDate);
      setRecordTab(sessionNumber === 1 ? "initial" : "session");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "통합 기록 생성에 실패했습니다.");
    } finally { setRecordBusy(false); }
  }

  async function finalizeRecord() {
    if (!records) return;
    const soapText = includeSoap ? soapFields.filter(field => soapDraft[field].trim()).map(field => `${field}: ${soapDraft[field].trim()}`).join("\n") : "";
    if (files.length && ocrResult && !ocrReviewed) return setError("SOAP 내용이 변경되었습니다. 원본 검수를 다시 완료하고 기록 초안을 재생성하세요.");
    if (generatedOCRSource !== `${soapText}\u0000${manualCorrection}`) return setError("SOAP 입력 또는 보완 메모가 초안 생성 후 변경되었습니다. 기록 초안을 다시 생성하세요.");
    setFinalizeBusy(true); setError("");
    try {
      const workflow = await finalizeSessionRecord(clientId, sessionNumber, records, includeSoap, files.map(file => file.name).join(", "), serviceDate);
      setFinalized(true);
      onFinalized?.(workflow.next_session_number);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "회기 기록 확정에 실패했습니다.");
    } finally { setFinalizeBusy(false); }
  }

  function updateRecord(group: "initial_intake" | "session_record" | "soap", field: string, value: string) {
    if (field === "상담일자") setServiceDate(value);
    setRecords(current => current ? { ...current, [group]: { ...current[group], [field]: value } } : current);
  }

  const recordsText = useMemo(() => records ? recordsToText(records) : "", [records]);
  const soapSourceText = includeSoap ? soapFields.filter(field => soapDraft[field].trim()).map(field => `${field}: ${soapDraft[field].trim()}`).join("\n") : "";
  const ocrRecordIsStale = Boolean(records && generatedOCRSource !== `${soapSourceText}\u0000${manualCorrection}`);
  const ocrReady = Boolean(ocrResult && ocrText.trim() && ocrReviewed);

  function selectFiles(selectedFiles: File[]) {
    setFiles(selectedFiles);
    setOCRResult(null);
    setOCRText("");
    setSoapDraft(emptySoapDraft);
    setOCRReviewed(false);
    setManualCorrection("");
    setRecords(null);
    setGeneratedOCRSource(null);
    setFinalized(false);
    setError("");
  }

  function updateSoapField(field: keyof SoapDraft, value: string) {
    setSoapDraft(current => ({ ...current, [field]: value }));
    setOCRText(current => current || "직접 입력 SOAP");
    setOCRReviewed(false);
  }

  return <section className="records-workspace">
    {activeStep === 3 && <Panel className="workflow-deck-card counseling-source-stage">
      <div className="workflow-card-kicker">3단계 · 상담자료 입력</div>
      <div className="panel-heading"><div><h2>이번 상담 내용을 입력하세요</h2><span>상담 메모는 필수이며, SOAP는 직접 입력하거나 사진·PDF로 추가할 수 있습니다.</span></div><Tag>{sourceLabel}</Tag></div>
      <label className="session-source-input">이번 상담 메모·음성 입력 텍스트<textarea rows={7} value={sessionText} onChange={event => setSessionText(event.target.value)} placeholder="실제 상담에서 확인한 내담자 보고, 상담사 관찰, 개입과 반응을 입력하세요."/></label>
      <label className={`optional-soap-toggle ${includeSoap ? "selected" : ""}`}><input type="checkbox" checked={includeSoap} onChange={event => { setIncludeSoap(event.target.checked); if (!event.target.checked) selectFiles([]); setError(""); }}/><span><b>SOAP 참고자료 추가</b><small>선택 사항 · 직접 입력하거나 작성한 문서를 업로드할 수 있습니다.</small></span></label>

      {includeSoap && <div className="optional-soap-workspace">
        <div className="soap-upload-toolbar">
          <div><b>SOAP 원본 업로드</b><span>{files.length ? `${files.length}개 파일 선택됨 · ${files.map(file => file.name).join(", ")}` : "선택한 파일이 없습니다. 직접 입력만 사용해도 됩니다."}</span></div>
          <label className="soap-file-button">파일 선택<input type="file" accept=".png,.jpg,.jpeg,.webp,.tif,.tiff,.pdf" multiple onChange={event => selectFiles(Array.from(event.target.files ?? []))}/></label>
          {files.length > 0 && <button type="button" onClick={() => selectFiles([])}>선택 취소</button>}
        </div>

        {files.length === 0
          ? <div className="soap-direct-entry"><div className="soap-entry-heading"><b>SOAP 직접 입력</b><span>사진을 선택하지 않으면 입력 내용만 상담기록지 생성에 반영됩니다.</span></div><SoapFieldsEditor values={soapDraft} onChange={updateSoapField}/></div>
          : <>
            {ocrStatus && !ocrStatus.available && <div className="service-connection-note">문서 인식 서비스 연결을 확인해 주세요. 오른쪽 입력란에는 직접 작성할 수 있습니다.</div>}
            <div className="soap-review-layout">
              <section className="soap-original-column"><div className="soap-column-heading"><b>원본 문서</b><span>선택한 실제 파일</span></div><DocumentPreviews filePreviews={filePreviews}/><button className="primary wide" type="button" onClick={extractOCR} disabled={ocrBusy || !ocrStatus?.available}>{ocrBusy ? "문서 인식 중…" : ocrResult ? "문서 인식 다시 실행" : "문서 인식 실행"}</button></section>
              <section className="soap-structured-column"><div className="soap-column-heading"><b>인식·수정 결과</b><span>{ocrResult ? "각 항목을 원본과 대조해 수정하세요." : "문서 인식 전에도 직접 입력할 수 있습니다."}</span></div><SoapFieldsEditor values={soapDraft} onChange={updateSoapField}/>
                {ocrResult && <><div className={`soap-safety-check ${ocrResult.risk_review_required ? "caution" : ""}`}><b>안전 관련 문구 확인</b><span>{ocrResult.risk_review_required ? "안전·위험 관련 문장은 부정 표현까지 포함해 원본과 비교해 주세요." : "인식된 안전 관련 문구를 원본과 대조해 주세요."}</span></div><label className={`ocr-review-confirm ${ocrReviewed ? "confirmed" : ""}`}><input type="checkbox" checked={ocrReviewed} onChange={event => setOCRReviewed(event.target.checked)}/><span><b>원본 대조 완료</b>원본 문서와 S/O/A/P 결과를 확인하고 필요한 내용을 수정했습니다.</span></label></>}
              </section>
            </div>
            {ocrResult && <label className="ocr-correction-note">누락·오류 보완 메모<textarea rows={3} value={manualCorrection} onChange={event => { setManualCorrection(event.target.value); setOCRReviewed(false); }} placeholder="수정한 문장과 확인 근거를 남깁니다."/></label>}
          </>}
      </div>}
      {error && <p className="form-error">{error}</p>}
      <StageNavigation step={3} onStepChange={onStepChange} nextDisabled={!sessionText.trim() || Boolean(includeSoap && files.length && !ocrReady)} nextLabel="다음: 기록 작성"/>
    </Panel>}

    {activeStep === 4 && <>
      <Panel className="workflow-deck-card">
        <div className="workflow-card-kicker">4단계 · 기록 작성</div>
        <div className="panel-heading"><div><h2>{sessionNumber === 1 ? "초기상담기록지 초안" : `${sessionNumber}회기 상담기록지 초안`}</h2><span>검수한 문서와 실제 회기 메모를 합쳐 편집 가능한 공식 기록을 만듭니다.</span></div><Tag>{sourceLabel}</Tag></div>
        <div className="record-workflow-guide"><b>{sessionNumber === 1 ? "필수 · 초기상담기록지" : "필수 · 상담기록지"}</b><span>SOAP는 참고자료이며, 필수 기록은 상담사가 확인한 뒤 확정합니다.</span></div>
        <div className="record-source-summary"><div><span>상담 메모</span><b>입력 완료</b></div><div><span>SOAP 참고자료</span><b>{includeSoap ? files.length ? "업로드·검수 반영" : "직접 입력 반영" : "사용하지 않음"}</b></div></div>
        <button className="primary wide" type="button" onClick={createRecords} disabled={recordBusy || Boolean(files.length && ocrResult && !ocrReviewed)}>{recordBusy ? "기록 초안을 만드는 중…" : records ? "상담기록지 초안 다시 생성" : sessionNumber === 1 ? "초기상담기록지 초안 생성" : "상담기록지 초안 생성"}</button>
        {error && <p className="form-error">{error}</p>}
      </Panel>

    {records && <Panel>
      <div className="panel-heading"><div><h2>편집 가능한 공식 기록</h2><span>생성된 초안을 원문과 직접 관찰에 대조한 후 확정합니다.</span></div><div className="record-heading-actions"><button type="button" onClick={() => window.print()}>양식 인쇄/PDF</button><Tag tone="green">초안 생성 완료</Tag></div></div>
      <div className="record-tabs">
        {sessionNumber === 1 && <button className={recordTab === "initial" ? "active" : ""} onClick={() => setRecordTab("initial")}>초기상담기록지</button>}
        {sessionNumber > 1 && <button className={recordTab === "session" ? "active" : ""} onClick={() => setRecordTab("session")}>상담기록지</button>}
        {includeSoap && <button className={recordTab === "soap" ? "active" : ""} onClick={() => setRecordTab("soap")}>SOAP 참고자료</button>}
        <button className={recordTab === "evidence" ? "active" : ""} onClick={() => setRecordTab("evidence")}>근거·확인사항</button>
      </div>
      <div className={`record-editor ${recordTab === "initial" || recordTab === "session" ? "official-layout" : ""}`}>
        {sessionNumber === 1 && recordTab === "initial" && <InitialIntakeForm values={records.initial_intake} onChange={(field, value) => updateRecord("initial_intake", field, value)} />}
        {sessionNumber > 1 && recordTab === "session" && <SessionRecordForm sessionNumber={sessionNumber} values={records.session_record} onChange={(field, value) => updateRecord("session_record", field, value)} />}
        {recordTab === "soap" && soapFields.map(field => <label key={field}><b>{field}</b><textarea value={records.soap[field] ?? ""} onChange={event => updateRecord("soap", field, event.target.value)} rows={6}/></label>)}
        {recordTab === "evidence" && <div className="evidence-grid"><div><h3>확인 필요 항목</h3>{records.uncertain_items.map(item => <p key={item}>• {item}</p>)}</div><div><h3>반영한 자료</h3>{Object.entries(records.source_summary).map(([key, value]) => <p key={key}><b>{key}</b><span>{value}</span></p>)}</div></div>}
      </div>
      <div className="session-finalize-box">
        <label>실제 상담일 <input type="date" value={serviceDate} onChange={event => { setServiceDate(event.target.value); updateRecord(sessionNumber === 1 ? "initial_intake" : "session_record", "상담일자", event.target.value); }} required/></label>
        <p>{includeSoap ? "필수 기록과 SOAP 참고자료를 함께 보관합니다." : "필수 기록만 보관합니다."} 확정된 기록은 다음 회기 준비자료에 반영됩니다.</p>
        {ocrRecordIsStale && <p className="form-error">OCR 전사문 또는 보완 메모가 바뀌었습니다. 변경 내용을 반영하도록 기록 초안을 다시 생성하세요.</p>}
        <button className="primary" type="button" onClick={finalizeRecord} disabled={finalizeBusy || finalized || ocrRecordIsStale || Boolean(files.length && ocrResult && !ocrReviewed)}>{finalized ? "회기 기록 확정 완료" : finalizeBusy ? "기록 확정 중…" : hasNextSession ? `기록 확정 및 ${sessionNumber + 1}회기 열기` : "최종 회기 기록 확정"}</button>
        {finalized && <Link className="record-return-link" href={`/counselor/clients/${clientId}`}>내담자 관리에서 확정 기록 보기 →</Link>}
      </div>
      <div className="download-row"><button onClick={() => downloadFile("integrated_records.txt", recordsText, "text/plain;charset=utf-8")}>통합 기록 문서</button><button onClick={() => downloadFile("integrated_records.json", JSON.stringify(records, null, 2), "application/json")}>통합 기록 백업</button><button onClick={() => downloadFile("document_text.txt", ocrText, "text/plain;charset=utf-8")} disabled={!ocrText}>문서 인식 정제문</button></div>
    </Panel>}
      <StageNavigation step={4} onStepChange={onStepChange} finalHref={`/counselor/clients/${clientId}`} finalDisabled={!records}/>
    </>}
  </section>;
}


function StageNavigation({ step, onStepChange, nextDisabled = false, nextLabel = "다음 단계", finalHref = "/counselor/clients", finalDisabled = false }: { step: number; onStepChange: (step: number) => void; nextDisabled?: boolean; nextLabel?: string; finalHref?: string; finalDisabled?: boolean }) {
  return <div className="workflow-nav"><button type="button" onClick={() => onStepChange(step - 1)}>← 이전</button><span>{step} / 4</span>{step < 4 ? <button className="primary" type="button" onClick={() => onStepChange(step + 1)} disabled={nextDisabled}>{nextLabel} →</button> : finalDisabled ? <button className="primary" type="button" disabled>상담기록지 작성 후 완료</button> : <Link className="primary" href={finalHref}>상담기록지 작성 완료 →</Link>}</div>;
}


function DocumentPreviews({ filePreviews }: { filePreviews: { name: string; type: string; url: string }[] }) {
  return <div className="ocr-document-previews prepared-ocr-preview" aria-label="업로드 원본 미리보기">{filePreviews.map(file => <figure key={file.url}><div className="ocr-preview-frame">{file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf") ? <iframe src={file.url} title={`${file.name} 원본 미리보기`}/> : /\.(png|jpe?g|webp)$/i.test(file.name) ? <a href={file.url} target="_blank" rel="noreferrer" aria-label={`${file.name} 원본 크게 보기`}><img src={file.url} alt={`${file.name} 원본 미리보기`}/></a> : <div className="ocr-preview-unavailable">브라우저 미리보기를 지원하지 않는 형식입니다.<br/>아래 버튼으로 원본 파일을 열어 확인하세요.</div>}</div><figcaption><span title={file.name}>{file.name}</span><a href={file.url} download={file.name}>다운로드</a></figcaption></figure>)}</div>;
}


const SOAP_LABELS: Record<keyof SoapDraft, string> = {
  S: "주관적 내용",
  O: "객관적 내용",
  A: "평가 내용",
  P: "계획 내용",
};


function SoapFieldsEditor({ values, onChange }: { values: SoapDraft; onChange: (field: keyof SoapDraft, value: string) => void }) {
  return <div className="structured-soap-fields">{soapFields.map(field => <label className={`soap-field-row field-${field.toLowerCase()}`} key={field}><span>{field}</span><div><b>{SOAP_LABELS[field]}</b><textarea rows={3} value={values[field]} onChange={event => onChange(field, event.target.value)} placeholder={`${field}: 내용을 입력하세요.`}/></div></label>)}</div>;
}


function parseSoapText(value: string): SoapDraft {
  const parsed: SoapDraft = { ...emptySoapDraft };
  const matches = value.matchAll(/(?:^|\n)\s*([SOAP])\s*:\s*([\s\S]*?)(?=\n\s*[SOAP]\s*:|$)/g);
  for (const match of matches) parsed[match[1] as keyof SoapDraft] = match[2].trim();
  return parsed;
}


function InitialIntakeForm({ values, onChange }: { values: Record<string, string>; onChange: (field: string, value: string) => void }) {
  return <article className="official-record-form initial-record-form">
    <header><h3>초기상담기록지</h3><p className="screen-only-form-guidance">생성된 초안을 원자료와 대조한 뒤 각 칸에서 수정하세요.</p></header>
    <section>
      <h4>1. 접수사항</h4>
      <div className="record-table-wrap"><table><tbody>
        <tr><th>사례<br/>번호</th><td><RecordInput value={values["사례번호"]} onChange={value => onChange("사례번호", value)} readOnly/></td><th>상담자</th><td><RecordInput value={values["상담자"]} onChange={value => onChange("상담자", value)} readOnly/></td></tr>
        <tr><th>상담<br/>일시</th><td><CounselingDateTime values={values} onChange={onChange}/></td><th>상담<br/>방법</th><td><RecordOptions name="initial-method" options={counselingMethods} value={values["상담방법"]} onChange={value => onChange("상담방법", value)}/></td></tr>
        <tr><th>상담<br/>유형</th><td colSpan={3}><RecordOptions name="initial-type" options={counselingTypes} value={values["상담유형"]} onChange={value => onChange("상담유형", value)}/></td></tr>
      </tbody></table></div>
    </section>
    <section>
      <h4>2. 주요내용</h4>
      <div className="record-table-wrap"><table className="initial-content-table"><tbody>
        <tr><th rowSpan={4}>내담자</th><th>성명</th><th>관계</th><th>성별</th></tr>
        {[1, 2, 3].map(index => <tr key={index}>
          <td><RecordInput value={values[`내담자${index} 성명`]} onChange={value => onChange(`내담자${index} 성명`, value)} placeholder={index === 1 ? "여러 명 입력 가능" : ""}/></td>
          <td><RecordInput value={values[`내담자${index} 관계`]} onChange={value => onChange(`내담자${index} 관계`, value)}/></td>
          <td><GenderOptions name={`initial-gender-${index}`} value={values[`내담자${index} 성별`]} onChange={value => onChange(`내담자${index} 성별`, value)}/></td>
        </tr>)}
        <tr><th>내담자<br/>호소문제(주제)</th><td colSpan={3}><RecordTextarea value={values[initialFields[0]]} onChange={value => onChange(initialFields[0], value)} rows={5}/></td></tr>
        <tr><th>상담목표<br/><small>(내담자와<br/>합의된 목표)</small></th><td colSpan={3}><RecordTextarea value={values[initialFields[1]]} onChange={value => onChange(initialFields[1], value)} rows={4}/></td></tr>
        <tr><th>상담계획</th><td colSpan={3}><RecordTextarea value={values[initialFields[2]]} onChange={value => onChange(initialFields[2], value)} rows={4}/></td></tr>
        <tr><th>상담내용</th><td colSpan={3}><RecordTextarea value={values[initialFields[3]]} onChange={value => onChange(initialFields[3], value)} rows={8}/></td></tr>
        <tr><th>가계도</th><td colSpan={3}><GenogramDiagram clientName={values["내담자1 성명"]} clientGender={values["내담자1 성별"]} familyText={values[initialFields[4]]} onChange={value => onChange(initialFields[4], value)}/></td></tr>
      </tbody></table></div>
      <p className="official-form-note">※ 초기상담 후 상담 기록에 활용</p>
    </section>
  </article>;
}


function SessionRecordForm({ sessionNumber, values, onChange }: { sessionNumber: number; values: Record<string, string>; onChange: (field: string, value: string) => void }) {
  return <article className="official-record-form session-record-form">
    <header><h3>상담기록지</h3><p className="screen-only-form-guidance">{sessionNumber}회기 기록 · 생성된 초안을 원자료와 대조한 뒤 수정하세요.</p></header>
    <div className="record-table-wrap"><table><tbody>
      <tr><th>상담자</th><td><RecordInput value={values["상담자"]} onChange={value => onChange("상담자", value)} readOnly/></td><th>내담자</th><td><RecordInput value={values["내담자"]} onChange={value => onChange("내담자", value)} placeholder="여러 명 입력 가능"/></td></tr>
      <tr><th rowSpan={2}>상담<br/>일시</th><td rowSpan={2}><CounselingDateTime values={values} onChange={onChange}/></td><th>상담<br/>회기</th><td><RecordInput value={values["상담회기"] || String(sessionNumber)} onChange={value => onChange("상담회기", value)}/></td></tr>
      <tr><th>연계<br/>기관</th><td><RecordInput value={values["접수 연계기관"]} onChange={value => onChange("접수 연계기관", value)}/></td></tr>
      <tr><th>상담<br/>방법</th><td><RecordOptions name="session-method" options={counselingMethods} value={values["상담방법"]} onChange={value => onChange("상담방법", value)}/></td><th>상담<br/>유형</th><td><RecordOptions name="session-type" options={counselingTypes} value={values["상담유형"]} onChange={value => onChange("상담유형", value)}/></td></tr>
      <tr className="topic-row"><th>상담<br/>주제</th><td colSpan={3}><div className="record-topic-grid">{sessionFields.slice(0, 3).map((field, index) => <label key={field}><span>[{index + 1}순위]</span><RecordTextarea value={values[field]} onChange={value => onChange(field, value)} rows={3}/></label>)}</div></td></tr>
      <tr><th>당회기<br/>상담 목표</th><td colSpan={3}><RecordTextarea value={values[sessionFields[3]]} onChange={value => onChange(sessionFields[3], value)} rows={5}/></td></tr>
      <tr><th rowSpan={3}>상담 내용<br/><small>(상담개입)</small></th><td colSpan={3}><RecordTextarea value={values[sessionFields[4]]} onChange={value => onChange(sessionFields[4], value)} rows={10}/></td></tr>
      <tr><th>다음 회기<br/>계획</th><td colSpan={2}><RecordTextarea value={values[sessionFields[5]]} onChange={value => onChange(sessionFields[5], value)} rows={7}/></td></tr>
      <tr><th>연계기관</th><td colSpan={2}><RecordTextarea value={values[sessionFields[6]]} onChange={value => onChange(sessionFields[6], value)} rows={4}/></td></tr>
    </tbody></table></div>
  </article>;
}


function CounselingDateTime({ values, onChange }: { values: Record<string, string>; onChange: (field: string, value: string) => void }) {
  return <div className="record-datetime">
    <RecordInput type="date" value={values["상담일자"]} onChange={value => onChange("상담일자", value)}/>
    <span><RecordInput type="time" value={values["상담시작시각"]} onChange={value => onChange("상담시작시각", value)}/> ~ <RecordInput type="time" value={values["상담종료시각"]} onChange={value => onChange("상담종료시각", value)}/></span>
  </div>;
}


function RecordOptions({ name, options, value = "", onChange }: { name: string; options: string[]; value?: string; onChange: (value: string) => void }) {
  return <div className="record-options">{options.map(option => <label key={option}><input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)}/><span>{option}</span></label>)}</div>;
}


function GenderOptions({ name, value = "", onChange }: { name: string; value?: string; onChange: (value: string) => void }) {
  return <div className="record-gender-options">{["남", "여"].map(option => <label key={option}><input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)}/><span>{option}</span></label>)}</div>;
}


function RecordInput({ value = "", onChange, type = "text", readOnly = false, placeholder = "" }: { value?: string; onChange: (value: string) => void; type?: "text" | "date" | "time"; readOnly?: boolean; placeholder?: string }) {
  return <input type={type} value={value} onChange={event => onChange(event.target.value)} readOnly={readOnly} placeholder={placeholder}/>;
}


function RecordTextarea({ value = "", onChange, rows }: { value?: string; onChange: (value: string) => void; rows: number }) {
  return <>
    <textarea className="record-screen-textarea" value={value} onChange={event => onChange(event.target.value)} rows={rows} maxLength={officialRecordFieldMaxLength}/>
    <div className="record-print-value" aria-hidden="true">{value || "\u00a0"}</div>
  </>;
}


function recordsToText(records: IntegratedRecords) {
  const lines: string[] = [];
  if (Object.keys(records.initial_intake).length) {
    lines.push("[초기상담기록지]");
    Object.entries(records.initial_intake).forEach(([key, value]) => lines.push(`${key}\n${value}`));
  }
  if (Object.keys(records.session_record).length) {
    lines.push("\n[상담기록지]");
    Object.entries(records.session_record).forEach(([key, value]) => lines.push(`${key}\n${value}`));
  }
  if (Object.keys(records.soap).length) {
    lines.push("\n[SOAP 일지]");
    Object.entries(records.soap).forEach(([key, value]) => lines.push(`${key}: ${value}`));
  }
  lines.push("\n[확인 필요 항목]", ...records.uncertain_items.map(item => `- ${item}`));
  return lines.join("\n");
}



function downloadFile(filename: string, data: string, mime: string) {
  const blob = new Blob(["\ufeff", data], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; anchor.click();
  URL.revokeObjectURL(url);
}
