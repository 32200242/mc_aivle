from __future__ import annotations

import importlib.util
import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import settings


FORM_BOILERPLATE = {
    "초기상담기록지": ["초기상담기록지", "접수사항", "호소문제", "가계도", "상담목표", "상담자 의견"],
    "상담기록지": ["상담기록지", "당회기 상담목표", "상담내용", "상담개입", "다음 회기 계획"],
    "SOAP 일지": ["SOAP", "Subjective", "Objective", "Assessment", "Plan", "Summary 요약"],
}


def ocr_status() -> dict[str, Any]:
    available = all(importlib.util.find_spec(name) is not None for name in ("easyocr", "PIL", "fitz", "cv2"))
    gpu_available = False
    try:
        import torch

        gpu_available = bool(torch.cuda.is_available())
    except Exception:
        pass
    detail = (
        "EasyOCR 이미지·PDF 추출을 사용할 수 있습니다."
        if available
        else "OCR 선택 패키지가 없습니다. 수동 텍스트 입력은 가능하며, backend/requirements-ocr.txt 설치 후 OCR을 사용할 수 있습니다."
    )
    return {
        "provider": settings.ocr_provider,
        "available": available,
        "detail": detail,
        "gpu_available": gpu_available,
    }


@lru_cache(maxsize=2)
def _load_reader(use_gpu: bool):
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError("EasyOCR가 설치되어 있지 않습니다. backend/requirements-ocr.txt를 설치하세요.") from exc
    return easyocr.Reader(["ko", "en"], gpu=use_gpu, verbose=False)


def _document_to_images(file_bytes: bytes, filename: str) -> list[tuple[str, Any]]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow가 설치되어 있지 않습니다.") from exc
    Image.MAX_IMAGE_PIXELS = 50_000_000
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PDF OCR을 위해 PyMuPDF가 필요합니다.") from exc
        document = fitz.open(stream=file_bytes, filetype="pdf")
        pages: list[tuple[str, Any]] = []
        try:
            for page_index in range(min(len(document), settings.ocr_max_pdf_pages)):
                page = document.load_page(page_index)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                pages.append((f"{filename} - {page_index + 1}쪽", image))
        finally:
            document.close()
        return pages
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    return [(filename, image)]


def _preprocess(image: Any, mode: str) -> Any:
    from PIL import Image

    image = image.convert("RGB")
    if image.width > 2600:
        ratio = 2600 / float(image.width)
        image = image.resize((2600, int(image.height * ratio)))
    if mode == "원본":
        return image
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("OCR 전처리를 위해 OpenCV가 필요합니다.") from exc
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    if mode == "대비 강화":
        processed = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    else:
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
        )
    return Image.fromarray(processed).convert("RGB")


def _items_to_lines(items: list[Any]) -> tuple[list[str], list[dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, text, confidence = item[0], str(item[1]).strip(), float(item[2])
        if not text or confidence < 0.10:
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        normalized.append({
            "x": min(xs), "y": sum(ys) / len(ys), "h": max(ys) - min(ys),
            "text": text, "confidence": round(confidence, 4),
        })
    normalized.sort(key=lambda item: (item["y"], item["x"]))
    lines: list[list[dict[str, Any]]] = []
    for item in normalized:
        if not lines:
            lines.append([item])
            continue
        current_y = sum(value["y"] for value in lines[-1]) / len(lines[-1])
        if abs(item["y"] - current_y) <= max(14.0, item["h"] * 0.7):
            lines[-1].append(item)
        else:
            lines.append([item])
    text_lines = [" ".join(value["text"] for value in sorted(line, key=lambda value: value["x"])) for line in lines]
    return text_lines, normalized


def detect_form_type(text: str) -> str:
    compact = re.sub(r"\s+", "", text or "").lower()
    if any(token in compact for token in ("soap", "subjective", "objective", "assessment")):
        return "SOAP 일지"
    if any(token in compact for token in ("초기상담기록지", "접수사항", "가계도")):
        return "초기상담기록지"
    if any(token in compact for token in ("당회기상담목표", "상담회기", "다음회기계획")):
        return "상담기록지"
    return "자유 노트"


def clean_form_boilerplate(text: str, selected_form: str = "자동 판별") -> tuple[str, str]:
    form_type = detect_form_type(text) if selected_form == "자동 판별" else selected_form
    labels = FORM_BOILERPLATE.get(form_type, [])
    normalized_labels = {re.sub(r"[^0-9a-z가-힣]", "", label.lower()) for label in labels}
    kept: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        compact = re.sub(r"[^0-9a-z가-힣]", "", stripped.lower())
        if compact in normalized_labels:
            continue
        if re.fullmatch(r"[□☐■▪•\-~※\s0-9년월일시분]+", stripped):
            continue
        kept.append(stripped)
    return "\n".join(kept).strip(), form_type


def run_ocr(
    documents: list[tuple[str, bytes]], preprocess_mode: str, selected_form: str, use_gpu: bool
) -> dict[str, Any]:
    if settings.ocr_provider != "easyocr":
        raise RuntimeError(f"지원하지 않는 OCR_PROVIDER입니다: {settings.ocr_provider}")
    reader = _load_reader(use_gpu)
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("OCR 처리를 위해 NumPy가 필요합니다.") from exc
    pages: list[dict[str, Any]] = []
    all_raw: list[str] = []
    all_clean: list[str] = []
    for filename, file_bytes in documents:
        for page_label, image in _document_to_images(file_bytes, filename):
            modes = ["원본", "대비 강화"] if preprocess_mode == "원본+대비 강화" else [preprocess_mode]
            page_lines: list[str] = []
            token_rows: list[dict[str, Any]] = []
            for mode in modes:
                result = reader.readtext(np.array(_preprocess(image, mode)), detail=1, paragraph=False)
                lines, tokens = _items_to_lines(result)
                page_lines.extend(lines)
                token_rows.extend({"page": page_label, "mode": mode, "text": token["text"], "confidence": token["confidence"]} for token in tokens)
            deduped: list[str] = []
            seen: set[str] = set()
            for line in page_lines:
                key = re.sub(r"\s+", "", line).lower()
                if key and key not in seen:
                    seen.add(key)
                    deduped.append(line)
            raw_text = "\n".join(deduped)
            clean_text, detected_form = clean_form_boilerplate(raw_text, selected_form)
            pages.append({
                "page": page_label, "detected_form": detected_form,
                "raw_text": raw_text, "clean_text": clean_text, "tokens": token_rows,
            })
            all_raw.append(f"[{page_label} / {detected_form}]\n{raw_text}")
            all_clean.append(f"[{page_label} / {detected_form}]\n{clean_text}")
    return {
        "provider": settings.ocr_provider,
        "raw_text": "\n\n".join(all_raw).strip(),
        "clean_text": "\n\n".join(all_clean).strip(),
        "pages": pages,
    }
