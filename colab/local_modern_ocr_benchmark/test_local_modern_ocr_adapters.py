import sys
import types
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from local_modern_ocr_adapters import (
    DeepSeekOCR2Adapter,
    GlmOCRAdapter,
    LightOnOCR2Adapter,
    PaddleOCRVL16Adapter,
    QWEN_OCR_PROMPT,
    Qwen3VLOCRAdapter,
    clean_ocr_text,
)


class LocalModernOCRAdapterTests(unittest.TestCase):
    def test_clean_ocr_text_removes_only_presentation_wrappers(self):
        value = "```text\n# 지난주 기록\n죽고 싶지 않다고 진술함.\n```"
        self.assertEqual(clean_ocr_text(value), "지난주 기록\n죽고 싶지 않다고 진술함.")

    def test_model_ids_are_pinned_to_reviewed_repositories(self):
        self.assertEqual(
            PaddleOCRVL16Adapter.model_id, "PaddlePaddle/PaddleOCR-VL-1.6"
        )
        self.assertEqual(GlmOCRAdapter.model_id, "zai-org/GLM-OCR")
        self.assertEqual(LightOnOCR2Adapter.model_id, "lightonai/LightOnOCR-2-1B")
        self.assertEqual(
            DeepSeekOCR2Adapter.model_id, "deepseek-community/DeepSeek-OCR-2"
        )
        self.assertEqual(Qwen3VLOCRAdapter.model_id, "Qwen/Qwen3-VL-4B-Instruct")

    def test_qwen_prompt_forbids_correction_and_invention(self):
        self.assertIn("고치거나", QWEN_OCR_PROMPT)
        self.assertIn("추론", QWEN_OCR_PROMPT)
        self.assertIn("전사문만", QWEN_OCR_PROMPT)

    def test_deepseek_native_adapter_uses_plain_ocr_prompt_and_trims_input(self):
        class FakeTensor:
            shape = (1, 2)

            def is_floating_point(self):
                return False

            def to(self, *args, **kwargs):
                return self

        class FakeProcessor:
            def __init__(self):
                self.last_text = None

            def __call__(self, *, images, text, return_tensors):
                del images, return_tensors
                self.last_text = text
                return {"input_ids": FakeTensor()}

            def decode(self, token_ids, skip_special_tokens):
                self.decoded_ids = token_ids
                self.skipped_special = skip_special_tokens
                return "```text\n# 인식 결과\n```"

        class FakeModel:
            def to(self, device):
                self.device = device
                return self

            def eval(self):
                return self

            def generate(self, **kwargs):
                del kwargs
                return [[100, 101, 200, 201]]

        processor = FakeProcessor()
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.AutoProcessor = types.SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: processor
        )
        fake_transformers.AutoModelForImageTextToText = types.SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: FakeModel()
        )
        fake_torch = types.SimpleNamespace(inference_mode=nullcontext)
        fake_image = types.SimpleNamespace(convert=lambda mode: object())

        with patch.dict(sys.modules, {"transformers": fake_transformers}), patch(
            "local_modern_ocr_adapters._runtime",
            return_value=(fake_torch, "cuda", "float16"),
        ), patch("local_modern_ocr_adapters.Image.open", return_value=fake_image):
            adapter = DeepSeekOCR2Adapter()
            result = adapter.predict("sample.png")

        self.assertEqual(processor.last_text, "<image>\nFree OCR.")
        self.assertEqual(processor.decoded_ids, [200, 201])
        self.assertTrue(processor.skipped_special)
        self.assertEqual(result, "인식 결과")


if __name__ == "__main__":
    unittest.main()
