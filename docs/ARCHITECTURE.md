# 아키텍처 및 확장 기준

## 권장 운영 구조

```text
브라우저(Next.js)
  ├─ 관리자 포털
  ├─ 상담사 업무 포털
  └─ 가상 내담자 교육 실습(첫 고정 영상 + 후속 생성 대화)
          │ HTTPS
API Gateway / FastAPI
  ├─ 인증·RBAC
  ├─ 내담자·회기·SOAP
  ├─ LLM 어댑터 ── 내부망 KT 믿:음(vLLM/OpenAI 호환) 서버
  ├─ OCR 어댑터 ── Colab 또는 KT GPU PaddleOCR-VL HTTP 서버
  └─ 아바타 어댑터 ── 선택적 LongCat-Video-Avatar 1.5 전용 GPU 워커
          │
PostgreSQL + Redis + Object Storage + Audit Log
```

프론트는 내담자 기록과 AI 공급자를 직접 호출하지 않습니다. 모든 호출을 백엔드를 통과시켜 권한, 감사로그, 비식별화와 장애 격리를 한곳에서 처리합니다.

## 현재 교육 실습 순서

1. 교육 페이지 진입 시 여성 가상 내담자와 부부갈등 실습 세션을 만듭니다.
2. 첫 기본 질문은 백엔드에서 고정 응답으로 판별하고, 응답 텍스트·비언어 행동·피드백을 동일하게 반환합니다.
3. 첫 응답 화면은 사전 제작 MP4를 즉시 재생하여 대기 없이 동일한 음성과 입모양을 보여줍니다.
4. 두 번째 턴부터는 믿:음 응답 스트림과 기존 TTS를 사용합니다. `AVATAR_PROVIDER=longcat_http`이고 별도 GPU 워커가 준비된 환경에서만 LongCat 영상을 비동기로 생성합니다.
5. 영상 또는 음성 서비스가 실패해도 감정별 기본 사진과 브라우저 음성으로 대화를 계속합니다.

## 선택적 LongCat 영상 워커

- 개발·기능 시험 기본값은 `AVATAR_PROVIDER=static_2d`이며 영상 모델을 전혀 로드하지 않습니다.
- 기존 Colab A100 영상 서버의 교체본은 `colab/LongCat_Avatar15_LowVRAM_Server_Colab.ipynb`입니다. FastAPI와 ngrok을 띄워 동일한 3개 HTTP 경로를 제공합니다.
- 전용 GPU가 있을 때만 `AVATAR_PROVIDER=longcat_http`와 `LONGCAT_AVATAR_BASE_URL`을 설정합니다.
- LongCat은 경량 립싱크 모델보다 훨씬 무거우므로 믿:음·OCR·TTS·STT 프로세스와 다른 Colab A100 런타임에 분리하고 작업 동시성을 1로 제한합니다.
- 백엔드는 `/v1/avatar/status`, `/v1/avatar/render`, `/v1/avatar/media/{filename}` 계약만 사용하므로 영상 워커 장애가 다른 기능을 막지 않습니다.
- 40GB급 단일 GPU 예제는 INT8·순차 오프로딩·480p 기본값을 사용하며, 충분한 GPU에서는 720p로 올릴 수 있습니다.
- LongCat은 실시간 립싱크 모델이 아니므로 첫 시연 응답은 사전 제작 MP4를 우선 사용해 생성 지연과 GPU 의존성을 제거합니다.

## 데이터 모델 권장안

- `organizations`, `centers`, `users`, `roles`, `user_roles`
- `clients`, `consents`, `cases`, `sessions`, `soap_notes`, `attachments`
- `training_personas`, `training_scenarios`, `training_sessions`, `training_turns`, `training_scores`
- `ai_jobs`, `model_versions`, `prompt_versions`, `audit_events`

실제 데이터에는 센터 단위 row-level security를 적용하고, 원문·요약·모델 입력을 구분 저장합니다. AI 요청에는 필요한 최소 정보만 전달합니다.

## 보안 체크리스트

- 공공기관 SSO 또는 OIDC와 MFA 적용
- 짧은 access token + 회전 refresh token, 서버 측 세션 폐기
- 역할뿐 아니라 센터·사례 소유권 단위 접근제어
- 개인정보와 상담기록 저장·전송 암호화
- 관리자 조회, 다운로드, AI 전송에 대한 불변 감사로그
- 파일 악성코드 검사와 허용 확장자·크기 제한
- 모델 프롬프트에 주민번호·연락처 등 직접식별자 전송 금지
- 백업 복구 훈련, 보존기간 및 파기 정책
- LLM/OCR 장애 시 상담 기록의 수동 입력 기능이 계속 동작하도록 circuit breaker 적용

## 단계별 전환

### 1단계 — 현재 세로 슬라이스

비식별 시연 데이터와 첫 고정 교육 영상으로 화면 흐름을 확정합니다. Colab은 믿:음, 후속 턴 음성·표현, PaddleOCR-VL 연동 검증에 사용합니다.

### 2단계 — 내부 개발망

PostgreSQL/Redis, OIDC, 내부 LLM/TTS, 오브젝트 스토리지를 붙입니다. 상담사 포털의 내담자·SOAP API부터 실데이터 계약 테스트를 수행합니다.

### 3단계 — 제한 운영

가상 페르소나 교육을 먼저 배포합니다. 실제 상담기록 기능은 비식별 샘플과 침투·권한·복구 테스트를 통과한 후 센터별로 점진 개방합니다.

### 4단계 — 전국 확장

센터별 테넌시, 중앙 집계의 비식별 통계, 모델·프롬프트 버전관리, 성능·편향 모니터링을 추가합니다.

## 2D 페르소나 자산 기준

- 실제 특정 인물과 무관한 성인 가상 인물
- 정면에 가깝고 눈썹·눈·입·턱선이 가려지지 않은 사진
- 감정 간 동일 인물·조명·구도·배경 유지
- 입은 다문 기본 사진을 사용하고 치아·손·머리카락이 입을 가리지 않도록 구성
- 교육 서비스 사용·수정·재생성 근거와 자산대장 보관

페르소나를 4~8명으로 늘릴 때는 사용자별 사진을 요청마다 base64로 저장하지 말고 암호화된 오브젝트 스토리지와 버전 메타데이터로 관리합니다.
