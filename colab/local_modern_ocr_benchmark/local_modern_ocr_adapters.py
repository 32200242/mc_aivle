"""Local modern OCR adapters for the SOAP handwriting benchmark.

Each adapter exposes ``name`` and ``predict(image_path, unit)`` so it can be
passed directly to ``soapbench.runner.run_inference``. Model dependencies are
imported lazily to keep the module importable during preflight validation.
"""

from __future__ import annotations

import gc
import re
from pathlib import Path
from typing import Any

from PIL import Image


QWEN_OCR_PROMPT = (
    "이미지에 실제로 보이는 한국어 손글씨만 읽는 순서대로 정확히 전사하세요. "
    "맞춤법을 고치거나 내용을 요약·추론·추가하지 마세요. "
    "설명과 마크다운 없이 전사문만 출력하세요."
)


def clean_ocr_text(text: str) -> str:
    """Remove presentation markup without rewriting OCR content."""

    value = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    value = re.sub(r"^```(?:text|markdown)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    lines: list[str] = []
    for line in value.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def _runtime() -> tuple[Any, str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA GPU is required for this Colab benchmark")
    device = "cuda"
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch, device, dtype


def _move_inputs(inputs: Any, device: str, dtype: Any) -> dict[str, Any]:
    moved: dict[str, Any] = {}
    for key, value in inputs.items():
        if hasattr(value, "is_floating_point") and value.is_floating_point():
            moved[key] = value.to(device=device, dtype=dtype)
        elif hasattr(value, "to"):
            moved[key] = value.to(device)
        else:
            moved[key] = value
    return moved


def _decode_new_tokens(processor: Any, inputs: dict[str, Any], output: Any) -> str:
    input_length = inputs["input_ids"].shape[-1]
    token_ids = output[0][input_length:]
    return clean_ocr_text(processor.decode(token_ids, skip_special_tokens=True))


class _ClosableAdapter:
    def close(self) -> None:
        for attribute in ("model", "processor", "tokenizer"):
            if hasattr(self, attribute):
                delattr(self, attribute)
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


class PaddleOCRVL16Adapter(_ClosableAdapter):
    """PaddleOCR-VL 1.6 using the native Transformers 5 implementation."""

    name = "PaddleOCR-VL-1.6-local"
    model_id = "PaddlePaddle/PaddleOCR-VL-1.6"

    def __init__(self, *, max_new_tokens: int = 512) -> None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.torch, self.device, self.dtype = _runtime()
        self.max_new_tokens = max_new_tokens
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
        ).to(self.device).eval()

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        image = Image.open(image_path).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "OCR:"},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        moved = _move_inputs(inputs, self.device, self.dtype)
        with self.torch.inference_mode():
            output = self.model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
            )
        return _decode_new_tokens(self.processor, moved, output)


class GlmOCRAdapter(_ClosableAdapter):
    """Z.ai GLM-OCR 0.9B, MIT licensed model weights."""

    name = "GLM-OCR-0.9B-local"
    model_id = "zai-org/GLM-OCR"

    def __init__(self, *, max_new_tokens: int = 512) -> None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.torch, self.device, self.dtype = _runtime()
        self.max_new_tokens = max_new_tokens
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
        ).to(self.device).eval()

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": str(Path(image_path).resolve())},
                    {"type": "text", "text": "Text Recognition:"},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs.pop("token_type_ids", None)
        moved = _move_inputs(inputs, self.device, self.dtype)
        with self.torch.inference_mode():
            output = self.model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
            )
        return _decode_new_tokens(self.processor, moved, output)


class LightOnOCR2Adapter(_ClosableAdapter):
    """LightOnOCR-2-1B, Apache-2.0 licensed end-to-end OCR."""

    name = "LightOnOCR-2-1B-local"
    model_id = "lightonai/LightOnOCR-2-1B"

    def __init__(self, *, max_new_tokens: int = 512) -> None:
        from transformers import (
            LightOnOcrForConditionalGeneration,
            LightOnOcrProcessor,
        )

        self.torch, self.device, self.dtype = _runtime()
        self.max_new_tokens = max_new_tokens
        self.processor = LightOnOcrProcessor.from_pretrained(self.model_id)
        self.model = LightOnOcrForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
        ).to(self.device).eval()

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        image = Image.open(image_path).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [{"type": "image", "image": image}],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        moved = _move_inputs(inputs, self.device, self.dtype)
        with self.torch.inference_mode():
            output = self.model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
            )
        return _decode_new_tokens(self.processor, moved, output)


class DeepSeekOCR2Adapter(_ClosableAdapter):
    """DeepSeek-OCR-2 via the Transformers-native community conversion.

    The original DeepSeek weights are Apache-2.0. The native conversion avoids
    the original checkpoint's Transformers 4.46/FlashAttention pin, allowing it
    to coexist with the Transformers 5 models in the same Colab runtime.
    """

    name = "DeepSeek-OCR-2-3B-local-hf-native-port"
    model_id = "deepseek-community/DeepSeek-OCR-2"

    def __init__(self, *, max_new_tokens: int = 512) -> None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.torch, self.device, self.dtype = _runtime()
        self.max_new_tokens = max_new_tokens
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
        ).to(self.device).eval()

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(
            images=image,
            text="<image>\nFree OCR.",
            return_tensors="pt",
        )
        moved = _move_inputs(inputs, self.device, self.dtype)
        with self.torch.inference_mode():
            output = self.model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
            )
        return _decode_new_tokens(self.processor, moved, output)


class Qwen3VLOCRAdapter(_ClosableAdapter):
    """Qwen3-VL-4B-Instruct multilingual OCR baseline, Apache-2.0."""

    name = "Qwen3-VL-4B-Instruct-local-ocr"
    model_id = "Qwen/Qwen3-VL-4B-Instruct"

    def __init__(self, *, max_new_tokens: int = 512) -> None:
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        self.torch, self.device, self.dtype = _runtime()
        self.max_new_tokens = max_new_tokens
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
        ).to(self.device).eval()

    def predict(self, image_path: str | Path, unit: Any = None) -> str:
        del unit
        image = Image.open(image_path).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": QWEN_OCR_PROMPT},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        moved = _move_inputs(inputs, self.device, self.dtype)
        with self.torch.inference_mode():
            output = self.model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
            )
        return _decode_new_tokens(self.processor, moved, output)


__all__ = [
    "DeepSeekOCR2Adapter",
    "GlmOCRAdapter",
    "LightOnOCR2Adapter",
    "PaddleOCRVL16Adapter",
    "Qwen3VLOCRAdapter",
    "clean_ocr_text",
]
