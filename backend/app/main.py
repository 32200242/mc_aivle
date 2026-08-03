from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import admin, auth, clients, copilot, documents, speech, training


app = FastAPI(
    title="가족센터 AI 상담 통합 플랫폼 API",
    version="0.1.0",
    description="교육 시뮬레이터 세로 슬라이스와 향후 내부망 연동용 API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(copilot.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(speech.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
