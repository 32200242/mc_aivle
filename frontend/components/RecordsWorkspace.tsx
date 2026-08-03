"use client";

import { useEffect, useMemo, useState } from "react";

import { generateCaseReport, generateIntegratedRecords, getOCRStatus, runOCR } from "@/lib/api";
import type { IntegratedRecords, OCRResult, OCRStatus, ReportResult } from "@/lib/types";
import { Panel, Tag } from "@/components/UI";


const initialFields = ["호소문제", "상담목표", "가족 및 관계 맥락", "주요 스트레스", "위험 및 보호요인", "초기 평가", "확인 필요 사항"];
const sessionFields = ["당회기 상담목표", "상담내용", "내담자 보고", "상담사 관찰", "상담개입", "내담자 반응", "과제", "다음 회기 계획"];
const soapFields = ["S", "O", "A", "P"] as const;
type RecordTab = "initial" | "session" | "soap" | "evidence";


export default function RecordsWorkspace({ sourceText, goal, note, sourceLabel }: { sourceText: string; goal: string; note: string; sourceLabel: string }) {
  const [ocrStatus, setOCRStatus] = useState<OCRStatus | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [formHint, setFormHint] = useState("자동 판별");
  const [preprocessMode, setPreprocessMode] = useState("문서 강화");
  const [useGpu, setUseGpu] = useState(false);
  const [ocrResult, setOCRResult] = useState<OCRResult | null>(null);
  const [ocrText, setOCRText] = useState("");
  const [manualCorrection, setManualCorrection] = useState("");
  const [existingSummary, setExistingSummary] = useState("");
  const [records, setRecords] = useState<IntegratedRecords | null>(null);
  const [recordTab, setRecordTab] = useState<RecordTab>("initial");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [caseSummary, setCaseSummary] = useState("");
  const [sessionChange, setSessionChange] = useState("");
  const [goalStatus, setGoalStatus] = useState("부분 달성");
  const [nextDate, setNextDate] = useState("");
  const [ocrBusy, setOCRBusy] = useState(false);
  const [recordBusy, setRecordBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { getOCRStatus().then(setOCRStatus).catch(() => undefined); }, []);

  async function extractOCR() {
    if (!files.length) return setError("이미지 또는 PDF를 먼저 선택하세요.");
    setOCRBusy(true); setError("");
    try {
      const result = await runOCR(files, preprocessMode, formHint, useGpu);
      setOCRResult(result);
      setOCRText(result.clean_text);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "OCR 처리에 실패했습니다.");
    } finally { setOCRBusy(false); }
  }

  async function createRecords() {
    if (!sourceText.trim() && !ocrText.trim() && !note.trim()) return setError("선택 사례 기록 또는 OCR 자료가 필요합니다.");
    setRecordBusy(true); setError("");
    try {
      const created = await generateIntegratedRecords({
        transcript: sourceText, session_goal: goal, counselor_note: note, ocr_text: ocrText,
        manual_correction: manualCorrection, existing_summary: existingSummary, form_hint: formHint,
      });
      setRecords(created);
      setCaseSummary(created.initial_intake["호소문제"] || "");
      setSessionChange(created.session_record["내담자 반응"] || "");
      setRecordTab("initial");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "통합 기록 생성에 실패했습니다.");
    } finally { setRecordBusy(false); }
  }

  async function createReport() {
    if (!records) return;
    setReportBusy(true); setError("");
    try {
      setReport(await generateCaseReport({
        records, case_summary: caseSummary, session_change: sessionChange,
        goal_status: goalStatus, next_date: nextDate || "미정",
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "보고서 생성에 실패했습니다.");
    } finally { setReportBusy(false); }
  }

  function updateRecord(group: "initial_intake" | "session_record" | "soap", field: string, value: string) {
    setRecords(current => current ? { ...current, [group]: { ...current[group], [field]: value } } : current);
  }

  const recordsText = useMemo(() => records ? recordsToText(records) : "", [records]);

  return <section className="records-workspace">
    <Panel>
      <div className="panel-heading"><div><h2>선택 사례 기록·OCR 통합</h2><span>{sourceLabel}에 OCR 자료가 있으면 추가하여 기록 초안을 생성합니다.</span></div><Tag tone={ocrStatus?.available ? "green" : "orange"}>{ocrStatus?.available ? "EasyOCR 사용 가능" : "OCR 선택 설치"}</Tag></div>
      {ocrStatus && <div className="inline-notice">{ocrStatus.detail}</div>}
      <div className="ocr-controls">
        <label>업로드 양식<select value={formHint} onChange={event => setFormHint(event.target.value)}><option>자동 판별</option><option>초기상담기록지</option><option>상담기록지</option><option>SOAP 일지</option><option>자유 노트</option></select></label>
        <label>OCR 전처리<select value={preprocessMode} onChange={event => setPreprocessMode(event.target.value)}><option>문서 강화</option><option>대비 강화</option><option>원본</option><option>원본+대비 강화</option></select></label>
        <label className="file-picker">이미지/PDF<input type="file" accept=".png,.jpg,.jpeg,.webp,.tif,.tiff,.pdf" multiple onChange={event => setFiles(Array.from(event.target.files ?? []))}/><span>{files.length ? `${files.length}개 파일 선택` : "파일 선택"}</span></label>
        <label className="check-label"><input type="checkbox" checked={useGpu} disabled={!ocrStatus?.gpu_available} onChange={event => setUseGpu(event.target.checked)}/> OCR GPU</label>
        <button className="primary" type="button" onClick={extractOCR} disabled={!files.length || ocrBusy || !ocrStatus?.available}>{ocrBusy ? "OCR 처리 중…" : "OCR 실행"}</button>
      </div>
      <div className="ocr-editor-grid">
        <label>OCR 정제 텍스트<textarea rows={12} value={ocrText} onChange={event => setOCRText(event.target.value)} placeholder="EasyOCR를 설치하지 않은 경우 기존 OCR 텍스트를 여기에 직접 붙여 넣을 수 있습니다."/></label>
        <label>OCR 누락·오인식 보완 메모<textarea rows={6} value={manualCorrection} onChange={event => setManualCorrection(event.target.value)} placeholder="손글씨 오인식이나 누락된 내용을 상담사가 직접 보완합니다."/><span>기존 기록 요약</span><textarea rows={4} value={existingSummary} onChange={event => setExistingSummary(event.target.value)} placeholder="이전 회기 요약이나 기존 기록"/></label>
      </div>
      {ocrResult?.pages.length ? <details><summary>OCR 원문·페이지·신뢰도 확인</summary><div className="ocr-page-list">{ocrResult.pages.map(page => <section key={page.page}><b>{page.page} · {page.detected_form}</b><pre>{page.raw_text}</pre><small>인식 토큰 {page.tokens.length}개 · 평균 신뢰도 {page.tokens.length ? (page.tokens.reduce((sum, token) => sum + token.confidence, 0) / page.tokens.length).toFixed(2) : "-"}</small></section>)}</div></details> : null}
      <button className="primary wide" type="button" onClick={createRecords} disabled={recordBusy}>{recordBusy ? "믿:음이 3종 기록을 통합하는 중…" : "초기상담기록지·상담기록지·SOAP 통합 초안 생성"}</button>
      {error && <p className="form-error">{error}</p>}
    </Panel>

    {records && <Panel>
      <div className="panel-heading"><div><h2>편집 가능한 통합 기록</h2><span>자동 초안은 상담사가 원문과 직접 관찰을 대조한 후 확정합니다.</span></div><Tag tone={records.provider === "mock" ? "gray" : "green"}>{records.provider === "mock" ? "규칙 기반 초안" : "믿:음 통합"}</Tag></div>
      <div className="record-tabs">
        <button className={recordTab === "initial" ? "active" : ""} onClick={() => setRecordTab("initial")}>초기상담기록지</button>
        <button className={recordTab === "session" ? "active" : ""} onClick={() => setRecordTab("session")}>상담기록지</button>
        <button className={recordTab === "soap" ? "active" : ""} onClick={() => setRecordTab("soap")}>SOAP 일지</button>
        <button className={recordTab === "evidence" ? "active" : ""} onClick={() => setRecordTab("evidence")}>근거·확인사항</button>
      </div>
      <div className="record-editor">
        {recordTab === "initial" && initialFields.map(field => <label key={field}>{field}<textarea value={records.initial_intake[field] ?? ""} onChange={event => updateRecord("initial_intake", field, event.target.value)} rows={4}/></label>)}
        {recordTab === "session" && sessionFields.map(field => <label key={field}>{field}<textarea value={records.session_record[field] ?? ""} onChange={event => updateRecord("session_record", field, event.target.value)} rows={4}/></label>)}
        {recordTab === "soap" && soapFields.map(field => <label key={field}><b>{field}</b><textarea value={records.soap[field] ?? ""} onChange={event => updateRecord("soap", field, event.target.value)} rows={6}/></label>)}
        {recordTab === "evidence" && <div className="evidence-grid"><div><h3>확인 필요 항목</h3>{records.uncertain_items.map(item => <p key={item}>• {item}</p>)}</div><div><h3>반영한 자료</h3>{Object.entries(records.source_summary).map(([key, value]) => <p key={key}><b>{key}</b><span>{value}</span></p>)}</div></div>}
      </div>
      <div className="download-row"><button onClick={() => downloadFile("integrated_records.txt", recordsText, "text/plain;charset=utf-8")}>통합 기록 TXT</button><button onClick={() => downloadFile("integrated_records.json", JSON.stringify(records, null, 2), "application/json")}>통합 기록 JSON</button><button onClick={() => downloadFile("ocr_clean_text.txt", ocrText, "text/plain;charset=utf-8")} disabled={!ocrText}>OCR 정제문</button></div>
    </Panel>}

    {records && <Panel>
      <div className="panel-heading"><div><h2>회기 요약·중간평가·종결 보고서</h2><span>기존 노트북의 보고서 생성 및 다운로드 기능</span></div></div>
      <div className="report-input-grid"><label>누적 사례 요약<textarea rows={4} value={caseSummary} onChange={event => setCaseSummary(event.target.value)}/></label><label>이번 회기 변화<textarea rows={4} value={sessionChange} onChange={event => setSessionChange(event.target.value)}/></label><label>목표 달성도<select value={goalStatus} onChange={event => setGoalStatus(event.target.value)}><option>미도달</option><option>부분 달성</option><option>대체로 달성</option><option>달성</option></select></label><label>다음 회기 예정일<input type="date" value={nextDate} onChange={event => setNextDate(event.target.value)}/></label></div>
      <button className="primary wide" type="button" onClick={createReport} disabled={reportBusy}>{reportBusy ? "보고서 생성 중…" : "회기·종결 보고서 생성"}</button>
      {report && <div className="report-output"><p className="inline-notice">{report.review_notice}</p><label>회기 요약 초안<textarea rows={12} value={report.session_report} onChange={event => setReport({ ...report, session_report: event.target.value })}/></label><label>중간평가/종결 초안<textarea rows={10} value={report.closing_report} onChange={event => setReport({ ...report, closing_report: event.target.value })}/></label><div className="download-row"><button onClick={() => downloadFile("case_report.txt", `${report.session_report}\n\n${report.closing_report}`, "text/plain;charset=utf-8")}>보고서 TXT 다운로드</button><button onClick={() => downloadFile("case_report.json", JSON.stringify(report, null, 2), "application/json")}>보고서 JSON 다운로드</button></div></div>}
    </Panel>}
  </section>;
}


function recordsToText(records: IntegratedRecords) {
  const lines = ["[초기상담기록지]"];
  Object.entries(records.initial_intake).forEach(([key, value]) => lines.push(`${key}\n${value}`));
  lines.push("\n[상담기록지]");
  Object.entries(records.session_record).forEach(([key, value]) => lines.push(`${key}\n${value}`));
  lines.push("\n[SOAP 일지]");
  Object.entries(records.soap).forEach(([key, value]) => lines.push(`${key}: ${value}`));
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
