"""Cloud OCR adapters for the standalone Colab benchmark.

The classes in this file intentionally implement only the tiny interface used by
``soapbench.runner.run_inference``: a ``name`` attribute and
``predict(image_path, unit) -> str``.
"""

from __future__ import annotations

import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Mapping

try:
    import requests
except ImportError:  # Lets response-shape tests run before Colab dependencies install.
    requests = None  # type: ignore[assignment]


def _non_empty_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def extract_upstage_text(payload: Mapping[str, Any]) -> str:
    """Extract text from both current and older Document OCR response shapes."""

    for key in ("text", "content"):
        text = _non_empty_text(payload.get(key))
        if text:
            return text

    page_texts: list[str] = []
    pages = payload.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, Mapping):
                continue
            text = _non_empty_text(page.get("text")) or _non_empty_text(
                page.get("content")
            )
            if text:
                page_texts.append(text)
    if page_texts:
        return "\n".join(page_texts)

    element_texts: list[str] = []
    elements = payload.get("elements")
    if isinstance(elements, list):
        for element in elements:
            if not isinstance(element, Mapping):
                continue
            text = _non_empty_text(element.get("text")) or _non_empty_text(
                element.get("content")
            )
            if text:
                element_texts.append(text)
    if element_texts:
        return "\n".join(element_texts)

    keys = ", ".join(sorted(str(key) for key in payload.keys()))
    raise ValueError(f"Upstage response did not contain OCR text (keys: {keys})")


def extract_azure_text(result: Any) -> str:
    """Extract text from an Azure AnalyzeResult without depending on SDK internals."""

    content = _non_empty_text(getattr(result, "content", None))
    if content:
        return content

    lines: list[str] = []
    for page in getattr(result, "pages", None) or []:
        for line in getattr(page, "lines", None) or []:
            text = _non_empty_text(getattr(line, "content", None))
            if text:
                lines.append(text)
    if lines:
        return "\n".join(lines)

    raise ValueError("Azure AnalyzeResult did not contain OCR text")


class AzureDocumentIntelligenceAdapter:
    """Azure Document Intelligence Read/Layout adapter."""

    def __init__(
        self,
        model_id: str,
        endpoint: str | None = None,
        key: str | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        if model_id not in {"prebuilt-read", "prebuilt-layout"}:
            raise ValueError("model_id must be 'prebuilt-read' or 'prebuilt-layout'")

        self.model_id = model_id
        self.name = f"azure-{model_id.removeprefix('prebuilt-')}"

        if client is not None:
            self._client = client
            return

        endpoint = (endpoint or os.getenv("AZURE_DOC_INTEL_ENDPOINT") or "").strip()
        key = (key or os.getenv("AZURE_DOC_INTEL_KEY") or "").strip()
        if not endpoint or not key:
            raise ValueError(
                "Azure credentials are missing. Set AZURE_DOC_INTEL_ENDPOINT and "
                "AZURE_DOC_INTEL_KEY in Colab Secrets."
            )

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as exc:  # pragma: no cover - exercised in Colab
            raise RuntimeError(
                "Install azure-ai-documentintelligence before using Azure OCR."
            ) from exc

        self._client = DocumentIntelligenceClient(
            endpoint=endpoint.rstrip("/"),
            credential=AzureKeyCredential(key),
        )

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        with Path(image_path).open("rb") as document:
            poller = self._client.begin_analyze_document(
                self.model_id,
                body=document,
            )
            result = poller.result()
        return extract_azure_text(result)


class UpstageDocumentOCRAdapter:
    """Upstage Document OCR adapter with bounded retry handling."""

    DEFAULT_ENDPOINT = "https://api.upstage.ai/v1/document-digitization"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_seconds: float = 180.0,
        max_retries: int = 4,
        session: Any | None = None,
    ) -> None:
        api_key = (api_key or os.getenv("UPSTAGE_API_KEY") or "").strip()
        if not api_key:
            raise ValueError(
                "Upstage API key is missing. Set UPSTAGE_API_KEY in Colab Secrets."
            )
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        self.name = "upstage-document-ocr"
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        if session is None:
            if requests is None:  # pragma: no cover - dependency is installed in Colab
                raise RuntimeError("Install requests before using Upstage OCR.")
            session = requests.Session()
        self._session = session
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def _post_once(self, image_path: Path, multipart_name: str) -> requests.Response:
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        with image_path.open("rb") as document:
            return self._session.post(
                self.endpoint,
                headers=self._headers,
                files={multipart_name: (image_path.name, document, mime_type)},
                data={"model": "ocr"},
                timeout=self.timeout_seconds,
            )

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        path = Path(image_path)
        last_response: requests.Response | None = None

        for attempt in range(self.max_retries + 1):
            response = self._post_once(path, "document")
            last_response = response

            if response.ok:
                payload = response.json()
                if not isinstance(payload, Mapping):
                    raise ValueError("Upstage response JSON was not an object")
                return extract_upstage_text(payload)

            # Older examples used the multipart key `image`. Retry once only when
            # the current endpoint explicitly rejects the request shape.
            if attempt == 0 and response.status_code in {400, 415, 422}:
                legacy_response = self._post_once(path, "image")
                last_response = legacy_response
                if legacy_response.ok:
                    payload = legacy_response.json()
                    if not isinstance(payload, Mapping):
                        raise ValueError("Upstage response JSON was not an object")
                    return extract_upstage_text(payload)
                response = legacy_response

            retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if not retryable or attempt >= self.max_retries:
                break

            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else min(2**attempt, 20)
            except ValueError:
                delay = min(2**attempt, 20)
            time.sleep(max(delay, 0.0))

        assert last_response is not None
        detail = last_response.text.replace("\n", " ")[:500]
        raise RuntimeError(
            f"Upstage OCR failed with HTTP {last_response.status_code}: {detail}"
        )


__all__ = [
    "AzureDocumentIntelligenceAdapter",
    "UpstageDocumentOCRAdapter",
    "extract_azure_text",
    "extract_upstage_text",
]
