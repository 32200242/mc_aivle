from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cloud_benchmark_adapters import (
    AzureDocumentIntelligenceAdapter,
    UpstageDocumentOCRAdapter,
    extract_azure_text,
    extract_upstage_text,
)


class FakeResponse:
    def __init__(self, status_code, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.multipart_names = []

    def post(self, *args, **kwargs):
        del args
        self.multipart_names.append(next(iter(kwargs["files"])))
        return self.responses.pop(0)


class AdapterTests(unittest.TestCase):
    def test_extract_upstage_current_and_legacy_shapes(self):
        self.assertEqual(extract_upstage_text({"text": " 현재 "}), "현재")
        self.assertEqual(
            extract_upstage_text({"pages": [{"text": "첫째"}, {"content": "둘째"}]}),
            "첫째\n둘째",
        )

    def test_extract_azure_content_and_line_fallback(self):
        self.assertEqual(extract_azure_text(SimpleNamespace(content=" 결과 ")), "결과")
        result = SimpleNamespace(
            content=None,
            pages=[SimpleNamespace(lines=[SimpleNamespace(content="한 줄")])],
        )
        self.assertEqual(extract_azure_text(result), "한 줄")

    def test_azure_adapter_uses_requested_model(self):
        result = SimpleNamespace(content="azure text")

        class Poller:
            def result(self):
                return result

        class Client:
            def __init__(self):
                self.model_id = None

            def begin_analyze_document(self, model_id, body):
                self.model_id = model_id
                self.body_was_open = not body.closed
                return Poller()

        client = Client()
        adapter = AzureDocumentIntelligenceAdapter("prebuilt-layout", client=client)
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "sample.png"
            image.write_bytes(b"not-an-image-but-the-adapter-only-streams-it")
            self.assertEqual(adapter.predict(image), "azure text")
        self.assertEqual(client.model_id, "prebuilt-layout")
        self.assertTrue(client.body_was_open)

    def test_upstage_retries_and_extracts_page_text(self):
        session = FakeSession(
            [
                FakeResponse(429, text="slow down", headers={"Retry-After": "0"}),
                FakeResponse(200, {"pages": [{"text": "upstage text"}]}),
            ]
        )
        adapter = UpstageDocumentOCRAdapter(
            api_key="secret", session=session, max_retries=1
        )
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "cloud_benchmark_adapters.time.sleep"
        ):
            image = Path(temp_dir) / "sample.png"
            image.write_bytes(b"bytes")
            self.assertEqual(adapter.predict(image), "upstage text")
        self.assertEqual(session.multipart_names, ["document", "document"])

    def test_upstage_legacy_multipart_fallback(self):
        session = FakeSession(
            [FakeResponse(422, text="missing image"), FakeResponse(200, {"text": "ok"})]
        )
        adapter = UpstageDocumentOCRAdapter(api_key="secret", session=session)
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "sample.jpg"
            image.write_bytes(b"bytes")
            self.assertEqual(adapter.predict(image), "ok")
        self.assertEqual(session.multipart_names, ["document", "image"])


if __name__ == "__main__":
    unittest.main()
