from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any

from ..config import settings


class LLMConfigurationError(RuntimeError):
    pass


def _clamp_max_tokens(max_tokens: int) -> int:
    """Keep every provider request within the configured server contract."""
    server_limit = max(1, int(getattr(settings, "llm_max_output_tokens", 1600)))
    return max(1, min(int(max_tokens), server_limit))


def _authorization_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if settings.internal_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.internal_llm_api_key}"
    return headers


def _models_endpoint() -> str:
    base = settings.internal_llm_base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return f"{base[:-len('/chat/completions')]}/models"
    return f"{base}/models"


def _probe_openai_sync() -> tuple[bool, str, int | None]:
    started = time.perf_counter()
    request = urllib.request.Request(_models_endpoint(), headers=_authorization_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=settings.llm_health_timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return False, f"모델 서버가 HTTP {exc.code}을 반환했습니다: {detail}", None
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        return False, f"모델 서버에 연결할 수 없습니다: {reason}", None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, f"모델 서버 상태 응답을 해석할 수 없습니다: {exc}", None
    latency_ms = round((time.perf_counter() - started) * 1000)
    if not isinstance(body.get("data"), list):
        return False, "모델 서버의 /v1/models 응답 형식이 올바르지 않습니다.", latency_ms
    return True, "Colab 믿:음 서버가 응답 중입니다.", latency_ms


def provider_status() -> dict[str, Any]:
    provider = settings.ai_provider
    if provider == "internal_openai":
        configured = bool(settings.internal_llm_base_url and settings.internal_llm_model)
        model = settings.internal_llm_model
        reachable: bool | None = None
        detail = (
            "모델 서버 주소와 모델명이 설정되었습니다."
            if configured
            else "INTERNAL_LLM_BASE_URL 또는 INTERNAL_LLM_MODEL이 비어 있습니다."
        )
        latency_ms: int | None = None
    elif provider == "midm_local":
        configured = True
        model = settings.midm_model_id
        reachable = None
        detail = "로컬 모델은 첫 생성 요청 때 로드됩니다."
        latency_ms = None
    else:
        configured = True
        model = "deterministic-demo"
        reachable = True
        detail = "화면 검증용 규칙 기반 데모 모드입니다."
        latency_ms = 0
    return {
        "provider": provider,
        "model": model,
        "configured": configured,
        "reachable": reachable,
        "detail": detail,
        "latency_ms": latency_ms,
    }


async def provider_status_with_probe() -> dict[str, Any]:
    status = provider_status()
    if status["provider"] == "internal_openai" and status["configured"]:
        reachable, detail, latency_ms = await asyncio.to_thread(_probe_openai_sync)
        status.update(reachable=reachable, detail=detail, latency_ms=latency_ms)
    return status


def _openai_chat_sync(messages: list[dict[str, str]], max_tokens: int, temperature: float) -> str:
    if not settings.internal_llm_base_url:
        raise LLMConfigurationError("INTERNAL_LLM_BASE_URL이 비어 있습니다.")
    base = settings.internal_llm_base_url.rstrip("/")
    endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    payload = json.dumps(
        {
            "model": settings.internal_llm_model or settings.midm_model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    headers = {**_authorization_headers(), "Content-Type": "application/json"}
    request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=settings.llm_request_timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"믿:음 API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"믿:음 API 연결 실패: {exc.reason}") from exc
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("믿:음 API 응답에 choices가 없습니다.")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, list):
        content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("믿:음 API 응답 content가 비어 있습니다.")
    return content.strip()


_LOCAL_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _load_local_midm():
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as exc:
        raise LLMConfigurationError(
            "로컬 믿:음 실행 패키지가 없습니다. pip install -r backend/requirements-midm.txt 를 실행하세요."
        ) from exc

    quantization_config = None
    if settings.midm_use_4bit and torch.cuda.is_available():
        try:
            compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        except Exception:
            quantization_config = None
    token = settings.midm_hf_token or None
    tokenizer = AutoTokenizer.from_pretrained(
        settings.midm_model_id,
        token=token,
        trust_remote_code=settings.midm_trust_remote_code,
    )
    kwargs: dict[str, Any] = {
        "token": token,
        "trust_remote_code": settings.midm_trust_remote_code,
        "low_cpu_mem_usage": True,
    }
    if torch.cuda.is_available():
        compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        kwargs.update({"device_map": "auto", "torch_dtype": compute_dtype})
    else:
        kwargs.update({"torch_dtype": torch.float32})
    if quantization_config is not None:
        kwargs["quantization_config"] = quantization_config
    model = AutoModelForCausalLM.from_pretrained(settings.midm_model_id, **kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model.eval()
    return torch, tokenizer, model


def _local_midm_sync(messages: list[dict[str, str]], max_tokens: int, temperature: float) -> str:
    torch, tokenizer, model = _load_local_midm()
    with _LOCAL_LOCK:
        inputs = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        if torch.cuda.is_available():
            inputs = {key: value.to(model.device) for key, value in inputs.items()}
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=max(0.01, temperature),
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        generated = outputs[0][inputs["input_ids"].shape[-1] :]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()


async def chat_completion(
    messages: list[dict[str, str]], max_tokens: int = 900, temperature: float = 0.45
) -> str:
    max_tokens = _clamp_max_tokens(max_tokens)
    if settings.ai_provider == "internal_openai":
        return await asyncio.to_thread(_openai_chat_sync, messages, max_tokens, temperature)
    if settings.ai_provider == "midm_local":
        return await asyncio.to_thread(_local_midm_sync, messages, max_tokens, temperature)
    raise LLMConfigurationError("현재 AI_PROVIDER가 mock입니다.")
