# 프로젝트 구조

## 구성 요소

| 경로 | 역할 |
|---|---|
| `backend/` | FastAPI 애플리케이션, 도메인 서비스, 데이터 생성 도구, 자동화 시험 |
| `frontend/` | Next.js 웹 애플리케이션, 역할별 화면, 정적 자산 |
| `contracts/` | 프런트엔드·백엔드 간 API 계약 |
| `colab/` | Mi:dm, PaddleOCR-VL, LongCat, 선택적 음성 서비스 실행 환경 |
| `workers/` | 장시간 GPU 작업을 분리하는 LongCat 아바타 워커 |
| `deploy/` | Docker, Render, Cloudflare Quick Tunnel 배포 구성 |
| `docs/` | 아키텍처, 데이터, 로컬 개발, AI 서비스 연동 문서 |

## 런타임 데이터

대시보드용 합성 데이터와 고정 미디어는 애플리케이션에 포함됩니다. 상담 사례 SQLite는 별도
데이터 자산으로 관리하며, `backend/scripts/build_counseling_dataset.py`로 동일한 스키마의
합성 데이터를 생성할 수 있습니다. 데이터 구조와 거버넌스는
[`DATA_CATALOG.md`](./DATA_CATALOG.md)를 참조하십시오.

다음 항목은 실행환경에서 생성하거나 안전한 비밀관리 수단으로 주입합니다.

- `.env`, API 키, 토큰, 인증 비밀값
- Python 가상환경과 Node.js 설치 결과
- Next.js 빌드 결과와 테스트·브라우저 캐시
- 교육 진행 상태와 로그
- 외부 AI 모델 가중치

## AI 서비스 구성

| 기능 | 기본 구성 요소 | 백엔드 설정 |
|---|---|---|
| LLM·OCR | `colab/Midm_Base_OpenAI_Server_Colab.ipynb` | `AI_PROVIDER`, `INTERNAL_LLM_*`, `OCR_PROVIDER`, `INTERNAL_OCR_*` |
| 아바타 영상 | `colab/LongCat_Avatar15_LowVRAM_Server_Colab.ipynb` | `AVATAR_PROVIDER=longcat_http`, `LONGCAT_AVATAR_*` |
| TTS·STT | `colab/optional_speech_services/Midm_Qwen3_TTS_ASR_MuseTalk_A100_Colab.ipynb` | `INTERNAL_TTS_*`, `STT_PROVIDER=qwen_http`, `INTERNAL_STT_*` |

GPU 서비스는 독립적으로 배치할 수 있습니다. 기본 로컬 구성은 `AI_PROVIDER=mock`과
`AVATAR_PROVIDER=static_2d`를 사용하므로 외부 모델 서버 없이 웹 기능을 확인할 수 있습니다.

## 배포 경계

현재 인증과 일부 상태 저장은 개발·검증 환경을 대상으로 합니다. 실제 기관 환경으로 전환할 때는
SSO/OIDC, 관리형 관계형 데이터베이스, 중앙 비밀관리, 감사로그, 백업·복구, 접근통제 정책을
운영 기준에 맞게 구성해야 합니다.
