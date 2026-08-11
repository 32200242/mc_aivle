from __future__ import annotations

import importlib.util
import base64
import io
import json
import re
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import settings


FORM_BOILERPLATE = {
    "초기상담기록지": ["초기상담기록지", "접수사항", "호소문제", "가계도", "상담목표", "상담자 의견"],
    "상담기록지": ["상담기록지", "당회기 상담목표", "상담내용", "상담개입", "다음 회기 계획"],
    "SOAP 일지": ["SOAP", "Subjective", "Objective", "Assessment", "Plan", "Summary 요약"],
}

SOAP_GUIDANCE_LINES = {
    "내담자의관점에서무엇을이야기했고행했는지",
    "상담주제들",
    "보고된증상들",
    "말",
    "정서",
    "행동",
    "관찰된증상들",
    "내담자평가",
    "주호소문제",
    "지난회기이후로의변화",
    "사용한개입",
    "상담목표를달성하기위한계획",
    "이후의방향",
    "과제",
    "다음회기일정",
}
SOAP_SECTION_NAMES = {
    "S": ("summary", "subjective", "요약"),
    "O": ("observation", "observatoin", "objective", "관찰"),
    "A": ("assessment", "평가"),
    "P": ("plan", "계획"),
}
OCR_TRANSCRIPTION_PROMPT = (
    "OCR:\n이미지에 실제로 보이는 내용을 원문 그대로 전사하세요. 요약하거나 추론하거나 맞춤법을 고치지 마세요. "
    "SOAP 양식이면 인쇄된 작성 안내, 영문 항목명, 예시 불릿은 제외하고 각 답변 칸에 작성된 내용만 "
    "S:, O:, A:, P: 네 줄로 구분해 출력하세요. 다른 문서라면 작성된 내용을 빠짐없이 전사하세요. "
    "설명이나 마크다운은 덧붙이지 마세요."
)

PADDLE_LOCAL_PROVIDERS = {"paddleocr_vl", "paddleocr-vl", "paddleocr_vl_1_6"}
PADDLE_HTTP_PROVIDERS = {"paddleocr_vl_http", "paddleocr-vl-http", "colab_paddleocr_vl"}
PADDLE_PROVIDERS = PADDLE_LOCAL_PROVIDERS | PADDLE_HTTP_PROVIDERS
RISK_TERMS = (
    "자해", "자살", "죽고 싶", "죽고싶", "살고 싶지", "살고싶지", "해칠", "위기",
    "안전", "위험", "폭력", "학대", "계획은 없", "계획이 없", "사고는 없",
)
KNOWN_CRITICAL_ERROR_FRAGMENTS = ("업엽고", "업엎고", "자사사", "자사사간", "자해 미")
BENCHMARK_NOTICE = (
    "PaddleOCR-VL 1.6 내부 192개 표본 평가의 중요 문구 정확도는 96.43%(81/84)로 "
    "자동 확정 기준 99%에 미달합니다. OCR 결과는 원본 대조·수정 후에만 기록에 반영할 수 있습니다."
)


def _ocr_endpoint() -> str:
    if settings.internal_ocr_url:
        return settings.internal_ocr_url.rstrip("/")
    base = settings.internal_llm_base_url.rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    if base.endswith("/v1"):
        return f"{base}/ocr"
    return f"{base}/v1/ocr"


def _ocr_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "1",
    }
    api_key = settings.internal_ocr_api_key or settings.internal_llm_api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _probe_remote_ocr() -> tuple[bool, str, bool]:
    endpoint = _ocr_endpoint()
    if not endpoint:
        return False, "INTERNAL_OCR_URL 또는 INTERNAL_LLM_BASE_URL이 비어 있습니다.", False
    status_url = f"{endpoint}/status"
    request = urllib.request.Request(status_url, headers=_ocr_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=settings.ocr_health_timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return False, f"원격 GPU OCR 서버가 HTTP {exc.code}을 반환했습니다: {detail}", False
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        return False, f"원격 GPU OCR 서버에 연결할 수 없습니다: {reason}", False
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, f"원격 GPU OCR 상태 응답을 해석할 수 없습니다: {exc}", False
    available = body.get("status") == "ok" and bool(body.get("available", True))
    gpu_available = bool(body.get("gpu_available", False))
    detail = str(body.get("detail") or (
        "원격 PaddleOCR-VL 1.6 서버가 응답 중입니다."
        if available else "원격 PaddleOCR-VL 1.6 서버가 준비되지 않았습니다."
    ))
    return available, detail, gpu_available


def ocr_status() -> dict[str, Any]:
    provider = settings.ocr_provider.lower()
    client_dependencies = ("PIL", "fitz", "cv2")
    client_available = all(importlib.util.find_spec(name) is not None for name in client_dependencies)
    gpu_available = False
    if provider in PADDLE_HTTP_PROVIDERS:
        remote_available, detail, gpu_available = _probe_remote_ocr() if client_available else (
            False,
            "이미지·PDF 전처리 패키지가 없습니다. backend/requirements-ocr.txt를 설치하세요.",
            False,
        )
        available = client_available and remote_available
    elif provider in PADDLE_LOCAL_PROVIDERS:
        dependencies = ("torch", "transformers", *client_dependencies)
        available = all(importlib.util.find_spec(name) is not None for name in dependencies)
        try:
            import torch

            gpu_available = bool(torch.cuda.is_available())
        except Exception:
            pass
        detail = (
            "로컬 PaddleOCR-VL 1.6이 준비되었습니다. 모든 결과는 원본 검수가 필요합니다."
            if available
            else "로컬 PaddleOCR-VL 실행 패키지가 없습니다. Colab HTTP 모드를 권장합니다."
        )
    else:
        dependencies = ("easyocr", *client_dependencies)
        available = all(importlib.util.find_spec(name) is not None for name in dependencies)
        detail = "EasyOCR가 준비되었습니다." if available else "OCR 실행 패키지가 없습니다."
    return {
        "provider": settings.ocr_provider,
        "available": available,
        "detail": detail,
        "gpu_available": gpu_available,
        "model_id": settings.paddle_ocr_model_id if provider in PADDLE_PROVIDERS else None,
        "review_required": True,
    }


@lru_cache(maxsize=2)
def _load_reader(use_gpu: bool):
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError("EasyOCR가 설치되어 있지 않습니다. backend/requirements-ocr.txt를 설치하세요.") from exc
    return easyocr.Reader(["ko", "en"], gpu=use_gpu, verbose=False)


class _PaddleOCRVLReader:
    def __init__(self, use_gpu: bool) -> None:
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR-VL 1.6 실행 패키지가 없습니다. backend/requirements-ocr.txt를 설치하세요."
            ) from exc

        self.torch = torch
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        self.dtype = (
            torch.bfloat16 if self.device == "cuda" and torch.cuda.is_bf16_supported()
            else torch.float16 if self.device == "cuda"
            else torch.float32
        )
        self.processor = AutoProcessor.from_pretrained(settings.paddle_ocr_model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            settings.paddle_ocr_model_id,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
        ).to(self.device).eval()

    def read(self, image: Any) -> str:
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image.convert("RGB")},
                {"type": "text", "text": OCR_TRANSCRIPTION_PROMPT},
            ],
        }]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        moved: dict[str, Any] = {}
        for key, value in inputs.items():
            if hasattr(value, "is_floating_point") and value.is_floating_point():
                moved[key] = value.to(device=self.device, dtype=self.dtype)
            elif hasattr(value, "to"):
                moved[key] = value.to(self.device)
            else:
                moved[key] = value
        input_length = moved["input_ids"].shape[-1]
        with self.torch.inference_mode():
            output = self.model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=settings.paddle_ocr_max_new_tokens,
            )
        return _clean_vlm_text(self.processor.decode(output[0][input_length:], skip_special_tokens=True))

    def read_many(self, images: list[Any]) -> list[str]:
        return [self.read(image) for image in images]


class _PaddleOCRVLHTTPReader:
    device = "colab-cuda"

    def read_many(self, images: list[Any]) -> list[str]:
        if not images:
            return []
        endpoint = _ocr_endpoint()
        if not endpoint:
            raise RuntimeError("원격 OCR 주소가 없습니다. INTERNAL_OCR_URL 또는 INTERNAL_LLM_BASE_URL을 설정하세요.")
        batch_size = max(1, min(int(settings.ocr_remote_batch_size), 8))
        texts: list[str] = []
        for start in range(0, len(images), batch_size):
            batch = images[start : start + batch_size]
            encoded_images: list[str] = []
            for image in batch:
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="PNG", optimize=True)
                encoded_images.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
            payload = json.dumps({"images": encoded_images}, ensure_ascii=False).encode("utf-8")
            request = urllib.request.Request(endpoint, data=payload, headers=_ocr_headers(), method="POST")
            try:
                with urllib.request.urlopen(request, timeout=settings.ocr_request_timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:800]
                raise RuntimeError(f"원격 PaddleOCR-VL HTTP {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"원격 PaddleOCR-VL 연결 실패: {exc.reason}") from exc
            batch_texts = body.get("texts")
            if not isinstance(batch_texts, list) or len(batch_texts) != len(batch):
                raise RuntimeError("원격 OCR 응답의 texts 개수가 요청 이미지 수와 다릅니다.")
            texts.extend(_clean_vlm_text(str(text)) for text in batch_texts)
        return texts


@lru_cache(maxsize=2)
def _load_paddle_reader(use_gpu: bool) -> _PaddleOCRVLReader:
    """모델을 요청마다 다시 올리지 않고 프로세스 수명 동안 재사용한다."""

    return _PaddleOCRVLReader(use_gpu)


@lru_cache(maxsize=1)
def _load_paddle_http_reader() -> _PaddleOCRVLHTTPReader:
    return _PaddleOCRVLHTTPReader()


def _clean_vlm_text(text: str) -> str:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    value = re.sub(r"^```(?:text|markdown)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    return "\n".join(re.sub(r"^\s{0,3}#{1,6}\s*", "", line).rstrip() for line in value.splitlines()).strip()


def _compact_text(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())


def _find_risk_terms(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", (text or "").lower())
    return [term for term in RISK_TERMS if re.sub(r"\s+", "", term) in compact]


def _page_review(
    primary_text: str,
    alternate_text: str | None,
    detected_form: str,
) -> tuple[list[str], list[str], bool]:
    reasons: list[str] = []
    combined = "\n".join(value for value in (primary_text, alternate_text or "") if value)
    risk_terms = _find_risk_terms(combined)
    compact_primary = _compact_text(primary_text)
    omission_suspected = False

    if len(compact_primary) < 12:
        omission_suspected = True
        reasons.append("인식 문장이 지나치게 짧아 필드 또는 문장 누락 가능성이 있습니다.")
    if detected_form == "SOAP 일지":
        reasons.append("SOAP의 S 필드는 위험 부정 문장 누락 사례가 있어 원본 대조가 필수입니다.")
    if risk_terms:
        reasons.append(f"위험·안전 관련 문구({', '.join(risk_terms)})가 있어 문장 전체를 확인해야 합니다.")
    if any(_compact_text(fragment) in _compact_text(combined) for fragment in KNOWN_CRITICAL_ERROR_FRAGMENTS):
        reasons.append("벤치마크에서 확인된 위험 문구 오인식 형태와 유사합니다.")

    if alternate_text is not None:
        compact_alternate = _compact_text(alternate_text)
        longer = max(len(compact_primary), len(compact_alternate), 1)
        length_ratio = min(len(compact_primary), len(compact_alternate)) / longer
        similarity = SequenceMatcher(None, compact_primary, compact_alternate).ratio()
        if length_ratio < 0.78 or (longer >= 20 and similarity < 0.82):
            omission_suspected = True
            reasons.append(
                "원본·강화본 재인식 결과의 길이 또는 내용 차이가 커 부분 문장 누락 가능성이 있습니다."
            )
    return list(dict.fromkeys(reasons)), list(dict.fromkeys(risk_terms)), omission_suspected


def _document_to_images(file_bytes: bytes, filename: str) -> tuple[list[tuple[str, Any]], list[str]]:
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
        warnings: list[str] = []
        try:
            if len(document) > settings.ocr_max_pdf_pages:
                warnings.append(
                    f"{filename}: 전체 {len(document)}쪽 중 앞 {settings.ocr_max_pdf_pages}쪽만 인식했습니다."
                )
            for page_index in range(min(len(document), settings.ocr_max_pdf_pages)):
                page = document.load_page(page_index)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                pages.append((f"{filename} - {page_index + 1}쪽", image))
        finally:
            document.close()
        return pages, warnings
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    return [(filename, image)], []


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
    soap_sections = set(re.findall(r"(?im)^\s*([SOAP])\s*[:：]", text or ""))
    if len(soap_sections) >= 2 or any(token in compact for token in ("soap", "subjective", "objective", "assessment")):
        return "SOAP 일지"
    if any(token in compact for token in ("초기상담기록지", "접수사항", "가계도")):
        return "초기상담기록지"
    if any(token in compact for token in ("당회기상담목표", "상담회기", "다음회기계획")):
        return "상담기록지"
    return "자유 노트"


def _normalize_form_line(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())


def _soap_section_line(line: str) -> tuple[str, str, bool] | None:
    """SOAP 머리글 또는 `S: 실제 내용`을 (구역, 내용, 양식 머리글 여부)로 분리합니다."""

    stripped = re.sub(r"^[\s•▪■□☐\-–—*]+", "", line).strip()
    exact_section = re.fullmatch(r"([SOAP])", stripped, flags=re.IGNORECASE)
    if exact_section:
        return exact_section.group(1).upper(), "", True
    match = re.match(r"^([SOAP])\s*[:：]\s*(.*)$", stripped, flags=re.IGNORECASE)
    if match:
        section = match.group(1).upper()
        remainder = match.group(2).strip()
        normalized_remainder = _normalize_form_line(remainder)
        template_names = SOAP_SECTION_NAMES[section]
        is_template = not remainder or any(
            normalized_remainder == _normalize_form_line(name)
            or normalized_remainder.startswith(_normalize_form_line(name))
            for name in template_names
        )
        return section, "" if is_template else remainder, is_template

    normalized = _normalize_form_line(stripped)
    for section, names in SOAP_SECTION_NAMES.items():
        if normalized in {_normalize_form_line(name) for name in names}:
            return section, "", True
    return None


def _clean_soap_text(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    template_present = any(
        (_soap_section_line(line) or ("", "", False))[2]
        or _normalize_form_line(line) in SOAP_GUIDANCE_LINES
        for line in lines
    )
    sections: dict[str, list[str]] = {section: [] for section in "SOAP"}
    current_section: str | None = None
    saw_section = False
    unsectioned: list[str] = []

    for line in lines:
        normalized = _normalize_form_line(line)
        if normalized in {"soap", "soap일지"}:
            continue
        section_line = _soap_section_line(line)
        if section_line:
            current_section, content, _ = section_line
            saw_section = True
            if content:
                sections[current_section].append(content)
            continue
        guidance_candidate = _normalize_form_line(re.sub(r"^[\s•▪■□☐\-–—*]+", "", line))
        if template_present and guidance_candidate in SOAP_GUIDANCE_LINES:
            continue
        if current_section:
            sections[current_section].append(line)
        else:
            unsectioned.append(line)

    if saw_section:
        if unsectioned and not any(sections.values()):
            sections["S"].extend(unsectioned)
        return "\n".join(
            f"{section}: {' '.join(sections[section]).strip()}".rstrip()
            for section in "SOAP"
        ).strip()
    return "\n".join(unsectioned).strip()


def clean_form_boilerplate(text: str, selected_form: str = "자동 판별") -> tuple[str, str]:
    form_type = detect_form_type(text) if selected_form == "자동 판별" else selected_form
    if form_type == "SOAP 일지":
        return _clean_soap_text(text), form_type
    labels = FORM_BOILERPLATE.get(form_type, [])
    normalized_labels = {_normalize_form_line(label) for label in labels}
    kept: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        compact = _normalize_form_line(stripped)
        if compact in normalized_labels:
            continue
        if re.fullmatch(r"[□☐■▪•\-~※\s0-9년월일시분]+", stripped):
            continue
        kept.append(stripped)
    return "\n".join(kept).strip(), form_type


def _run_easyocr(
    documents: list[tuple[str, bytes]], preprocess_mode: str, selected_form: str, use_gpu: bool
) -> dict[str, Any]:
    reader = _load_reader(use_gpu)
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("OCR 처리를 위해 NumPy가 필요합니다.") from exc
    pages: list[dict[str, Any]] = []
    warnings: list[str] = []
    all_raw: list[str] = []
    all_clean: list[str] = []
    for filename, file_bytes in documents:
        document_pages, document_warnings = _document_to_images(file_bytes, filename)
        warnings.extend(document_warnings)
        for page_label, image in document_pages:
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
            review_reasons, risk_terms, omission_suspected = _page_review(raw_text, None, detected_form)
            pages.append({
                "page": page_label, "detected_form": detected_form,
                "raw_text": raw_text, "clean_text": clean_text, "tokens": token_rows,
                "alternate_text": None,
                "review_reasons": review_reasons,
                "risk_terms": risk_terms,
                "omission_suspected": omission_suspected,
            })
            all_raw.append(f"[{page_label} / {detected_form}]\n{raw_text}")
            all_clean.append(clean_text)
    review_reasons = list(dict.fromkeys(reason for page in pages for reason in page["review_reasons"]))
    return {
        "provider": settings.ocr_provider,
        "raw_text": "\n\n".join(all_raw).strip(),
        "clean_text": "\n\n".join(all_clean).strip(),
        "pages": pages,
        "warnings": [BENCHMARK_NOTICE, *warnings],
        "requires_review": True,
        "risk_review_required": any(page["risk_terms"] or page["detected_form"] == "SOAP 일지" for page in pages),
        "omission_suspected": any(page["omission_suspected"] for page in pages),
        "review_reasons": review_reasons,
        "benchmark_notice": BENCHMARK_NOTICE,
    }


def _run_paddle_ocr(
    documents: list[tuple[str, bytes]], preprocess_mode: str, selected_form: str, use_gpu: bool
) -> dict[str, Any]:
    provider = settings.ocr_provider.lower()
    reader = _load_paddle_http_reader() if provider in PADDLE_HTTP_PROVIDERS else _load_paddle_reader(use_gpu)
    pages: list[dict[str, Any]] = []
    warnings: list[str] = [BENCHMARK_NOTICE]
    all_raw: list[str] = []
    all_clean: list[str] = []

    if provider in PADDLE_LOCAL_PROVIDERS and use_gpu and reader.device != "cuda":
        warnings.append("CUDA GPU를 찾지 못해 CPU로 실행했습니다. 처리 시간이 크게 늘어날 수 있습니다.")

    page_sources: list[tuple[str, Any]] = []
    for filename, file_bytes in documents:
        document_pages, document_warnings = _document_to_images(file_bytes, filename)
        warnings.extend(document_warnings)
        page_sources.extend(document_pages)

    force_second_pass = preprocess_mode == "원본+대비 강화"
    primary_mode = "원본" if force_second_pass else preprocess_mode
    primary_images = [_preprocess(image, primary_mode) for _, image in page_sources]
    primary_texts = reader.read_many(primary_images)

    retry_indices: list[int] = []
    for index, primary_text in enumerate(primary_texts):
        _, preliminary_form = clean_form_boilerplate(primary_text, selected_form)
        if (
            force_second_pass
            or preliminary_form == "SOAP 일지"
            or bool(_find_risk_terms(primary_text))
            or len(_compact_text(primary_text)) < 30
        ):
            retry_indices.append(index)
    alternate_mode = "대비 강화" if primary_mode == "원본" else "원본"
    alternate_images = [_preprocess(page_sources[index][1], alternate_mode) for index in retry_indices]
    alternate_results = reader.read_many(alternate_images)
    alternates_by_index = dict(zip(retry_indices, alternate_results, strict=True))

    for index, ((page_label, _), primary_text) in enumerate(zip(page_sources, primary_texts, strict=True)):
        candidate = alternates_by_index.get(index)
        alternate_text = candidate if candidate is not None and _compact_text(candidate) != _compact_text(primary_text) else None
        chosen_text = primary_text
        if alternate_text:
            compact_primary = _compact_text(primary_text)
            compact_alternate = _compact_text(alternate_text)
            if not compact_primary or (
                len(compact_alternate) > len(compact_primary)
                and compact_primary in compact_alternate
            ):
                chosen_text = alternate_text

        clean_text, detected_form = clean_form_boilerplate(chosen_text, selected_form)
        other_variant = primary_text if chosen_text == alternate_text else alternate_text
        review_reasons, risk_terms, omission_suspected = _page_review(
            chosen_text, other_variant, detected_form
        )
        pages.append({
            "page": page_label,
            "detected_form": detected_form,
            "raw_text": chosen_text,
            "clean_text": clean_text,
            "tokens": [],
            "alternate_text": other_variant,
            "review_reasons": review_reasons,
            "risk_terms": risk_terms,
            "omission_suspected": omission_suspected,
        })
        all_raw.append(f"[{page_label} / {detected_form}]\n{chosen_text}")
        all_clean.append(clean_text)

    review_reasons = list(dict.fromkeys(reason for page in pages for reason in page["review_reasons"]))
    risk_review_required = any(page["risk_terms"] or page["detected_form"] == "SOAP 일지" for page in pages)
    omission_suspected = any(page["omission_suspected"] for page in pages)
    if risk_review_required:
        warnings.append("S 필드 또는 위험·안전 문구가 감지되었습니다. 부정 표현을 포함한 문장 전체를 원본과 대조하세요.")
    if omission_suspected:
        warnings.append("재인식 결과 차이 또는 짧은 출력이 감지되었습니다. 부분 문장 누락 여부를 확인하세요.")
    return {
        "provider": settings.ocr_provider,
        "raw_text": "\n\n".join(all_raw).strip(),
        "clean_text": "\n\n".join(all_clean).strip(),
        "pages": pages,
        "warnings": list(dict.fromkeys(warnings)),
        "requires_review": True,
        "risk_review_required": risk_review_required,
        "omission_suspected": omission_suspected,
        "review_reasons": review_reasons,
        "benchmark_notice": BENCHMARK_NOTICE,
    }


def run_ocr(
    documents: list[tuple[str, bytes]], preprocess_mode: str, selected_form: str, use_gpu: bool
) -> dict[str, Any]:
    provider = settings.ocr_provider.lower()
    if provider in PADDLE_PROVIDERS:
        return _run_paddle_ocr(documents, preprocess_mode, selected_form, use_gpu)
    if provider == "easyocr":
        return _run_easyocr(documents, preprocess_mode, selected_form, use_gpu)
    raise RuntimeError(f"지원하지 않는 OCR_PROVIDER입니다: {settings.ocr_provider}")
