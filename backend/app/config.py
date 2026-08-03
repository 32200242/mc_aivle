from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000")
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    internal_llm_base_url: str = os.getenv("INTERNAL_LLM_BASE_URL", "").rstrip("/")
    internal_llm_model: str = os.getenv("INTERNAL_LLM_MODEL", "")
    internal_llm_api_key: str = os.getenv("INTERNAL_LLM_API_KEY", "")
    internal_tts_url: str = os.getenv("INTERNAL_TTS_URL", "")
    ocr_provider: str = os.getenv("OCR_PROVIDER", "easyocr")
    ocr_max_file_mb: int = int(os.getenv("OCR_MAX_FILE_MB", "12"))
    ocr_max_pdf_pages: int = int(os.getenv("OCR_MAX_PDF_PAGES", "12"))
    stt_provider: str = os.getenv("STT_PROVIDER", "browser")
    internal_stt_url: str = os.getenv("INTERNAL_STT_URL", "")
    internal_stt_api_key: str = os.getenv("INTERNAL_STT_API_KEY", "")
    stt_request_timeout: float = float(os.getenv("STT_REQUEST_TIMEOUT", "120"))
    midm_model_id: str = os.getenv("MIDM_MODEL_ID", "K-intelligence/Midm-2.0-Base-Instruct")
    midm_hf_token: str = os.getenv("MIDM_HF_TOKEN", "")
    midm_use_4bit: bool = os.getenv("MIDM_USE_4BIT", "true").lower() in {"1", "true", "yes", "on"}
    midm_trust_remote_code: bool = os.getenv("MIDM_TRUST_REMOTE_CODE", "true").lower() in {"1", "true", "yes", "on"}
    llm_request_timeout: float = float(os.getenv("LLM_REQUEST_TIMEOUT", "180"))
    llm_health_timeout: float = float(os.getenv("LLM_HEALTH_TIMEOUT", "8"))
    auth_secret: str = os.getenv("AUTH_SECRET", "development-only-secret")


settings = Settings()
