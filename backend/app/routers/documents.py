from __future__ import annotations

import asyncio
import base64
import binascii
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from ..auth import CounselorUser
from ..config import settings
from ..schemas import FinalizeSessionRequest, IntegratedRecords, OCRRequest, OCRResult, OCRStatus, RecordGenerateRequest, ReportGenerateRequest, ReportResult, SessionWorkflow
from ..services.ocr import ocr_status, run_ocr
from ..services.linked_data import can_access_client
from ..services.records import generate_records, generate_report, official_record_fields
from ..services.session_workflow import dispatch_pending_completion_events, finalize_session, get_workflow
from ..synthetic_cases import get_client_case


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/workflow/{client_id}", response_model=SessionWorkflow)
def session_workflow(client_id: str, user: CounselorUser) -> SessionWorkflow:
    case = get_client_case(client_id)
    if not case or not can_access_client(user, client_id):
        raise HTTPException(status_code=404, detail="내담자 사례를 찾을 수 없습니다.")
    return get_workflow(client_id, len(case.sessions), case.current_session_number)


@router.post("/workflow/{client_id}/sessions/{session_number}/finalize", response_model=SessionWorkflow)
def finalize_session_record(
    client_id: str,
    session_number: Annotated[int, Path(ge=1)],
    request: FinalizeSessionRequest,
    user: CounselorUser,
) -> SessionWorkflow:
    case = get_client_case(client_id)
    if not case or not can_access_client(user, client_id):
        raise HTTPException(status_code=404, detail="내담자 사례를 찾을 수 없습니다.")
    try:
        session = next((item for item in case.sessions if item.number == session_number), None)
        if session is None:
            raise HTTPException(status_code=404, detail="선택한 회기를 찾을 수 없습니다.")
        workflow = finalize_session(
            client_id,
            session_number,
            len(case.sessions),
            case.current_session_number,
            request,
            len(session.participants),
            session.date,
            official_record_fields(case, session, user.name),
        )
        dispatch_pending_completion_events(f"{client_id}:{session_number}")
        return workflow
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/ocr/status", response_model=OCRStatus)
def get_ocr_status(user: CounselorUser) -> OCRStatus:
    return OCRStatus.model_validate(ocr_status())


@router.post("/ocr", response_model=OCRResult)
async def extract_ocr(
    request: OCRRequest,
    user: CounselorUser,
) -> OCRResult:
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".pdf"}
    documents: list[tuple[str, bytes]] = []
    for upload in request.documents:
        filename = upload.filename
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in allowed:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {filename}")
        try:
            content = base64.b64decode(upload.data_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"{filename}: Base64 파일 데이터가 올바르지 않습니다.") from exc
        if len(content) > settings.ocr_max_file_mb * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"{filename}: {settings.ocr_max_file_mb}MB 제한을 초과했습니다.")
        documents.append((filename, content))
    try:
        result = await asyncio.to_thread(
            run_ocr, documents, request.preprocess_mode, request.form_hint, request.use_gpu
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return OCRResult.model_validate(result)


@router.post("/records/generate", response_model=IntegratedRecords)
async def create_records(request: RecordGenerateRequest, user: CounselorUser) -> IntegratedRecords:
    try:
        if request.ocr_text.strip() and not request.ocr_reviewed:
            raise HTTPException(
                status_code=409,
                detail="OCR 텍스트는 업로드 원본과 대조하고 누락·오류를 수정한 뒤 검수 완료로 표시해야 합니다.",
            )
        case = None
        session = None
        if request.client_id:
            case = get_client_case(request.client_id)
            if not case or not can_access_client(user, request.client_id):
                raise HTTPException(status_code=404, detail="내담자 사례를 찾을 수 없습니다.")
            session = next(
                (item for item in case.sessions if item.number == request.session_number),
                None,
            )
            if request.session_number is not None and session is None:
                raise HTTPException(status_code=404, detail="선택한 회기를 찾을 수 없습니다.")
        return await generate_records(request, case=case, session=session, counselor_name=user.name)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/reports/generate", response_model=ReportResult)
async def create_report(request: ReportGenerateRequest, user: CounselorUser) -> ReportResult:
    try:
        return await generate_report(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
