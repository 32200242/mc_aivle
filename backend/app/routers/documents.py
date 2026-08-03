from __future__ import annotations

import asyncio
import base64
import binascii

from fastapi import APIRouter, HTTPException

from ..auth import TrainingUser
from ..config import settings
from ..schemas import IntegratedRecords, OCRRequest, OCRResult, OCRStatus, RecordGenerateRequest, ReportGenerateRequest, ReportResult
from ..services.ocr import ocr_status, run_ocr
from ..services.records import generate_records, generate_report


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/ocr/status", response_model=OCRStatus)
def get_ocr_status(user: TrainingUser) -> OCRStatus:
    return OCRStatus.model_validate(ocr_status())


@router.post("/ocr", response_model=OCRResult)
async def extract_ocr(
    request: OCRRequest,
    user: TrainingUser,
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
async def create_records(request: RecordGenerateRequest, user: TrainingUser) -> IntegratedRecords:
    try:
        return await generate_records(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/reports/generate", response_model=ReportResult)
async def create_report(request: ReportGenerateRequest, user: TrainingUser) -> ReportResult:
    try:
        return await generate_report(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
