# 아키텍처 및 확장 기준

## 권장 운영 구조

```text
브라우저(Next.js)
  ├─ 관리자 포털
  ├─ 상담사 업무 포털
  └─ 페르소나 교육 + Three.js GLB
          │ HTTPS / SSE
API Gateway / FastAPI
  ├─ 인증·RBAC
  ├─ 내담자·회기·SOAP
  ├─ 교육 세션·평가
  ├─ LLM 어댑터 ── 내부망 KT 믿:음(vLLM/OpenAI 호환) 서버
  └─ TTS 어댑터 ── 내부망 TTS 서버
          │
PostgreSQL + Redis + Object Storage + Audit Log
```

프론트는 내담자 기록과 AI 공급자를 직접 호출하지 않습니다. 모든 호출을 백엔드를 통과시켜 권한, 감사로그, 비식별화와 장애 격리를 한곳에서 처리합니다.

## 교육 턴 이벤트 순서

1. 프론트가 상담사 발화를 `POST /training/sessions/{id}/turns/stream`으로 전송합니다.
2. 서버는 `turn.started`를 보냅니다.
3. 생성되는 텍스트를 `response.delta`로 전송합니다. 화면에 즉시 누적됩니다.
4. 구조화된 감정·행동·피드백을 `turn.completed`로 보냅니다. 아바타 포즈와 표정을 즉시 바꿉니다.
5. `tts.ready`를 보냅니다. 사내 TTS가 있으면 음원 URL/데이터를 재생하고, 없으면 브라우저 TTS를 사용합니다.

이벤트 정의는 `contracts/avatar-event.schema.json`에 고정했습니다. AI 모델을 교체해도 프론트와 3D 엔진은 이 계약만 유지하면 됩니다.

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
- LLM/TTS 장애 시 상담 기록 기능이 계속 동작하도록 circuit breaker 적용

## 단계별 전환

### 1단계 — 현재 세로 슬라이스

가짜 데이터와 mock AI로 화면·이벤트·아바타 동작을 확정합니다. Colab/Streamlit은 표정·행동 실험 도구로 유지합니다.

### 2단계 — 내부 개발망

PostgreSQL/Redis, OIDC, 내부 LLM/TTS, 오브젝트 스토리지를 붙입니다. 상담사 포털의 내담자·SOAP API부터 실데이터 계약 테스트를 수행합니다.

### 3단계 — 제한 운영

가상 페르소나 교육을 먼저 배포합니다. 실제 상담기록 기능은 비식별 샘플과 침투·권한·복구 테스트를 통과한 후 센터별로 점진 개방합니다.

### 4단계 — 전국 확장

센터별 테넌시, 중앙 집계의 비식별 통계, 모델·프롬프트 버전관리, 성능·편향 모니터링을 추가합니다.

## 아바타 자산 기준

현재 모델은 `frontend/public/models/Female_Adult_01_facial_1024.glb`입니다. 새 모델은 다음을 만족해야 합니다.

- 성인 가상 인물이며 실제 특정 인물과 무관함
- GLB 내부 humanoid 계열 뼈 이름 또는 별도 매핑 제공
- ARKit 52 blendshape 또는 의미가 명확한 동등 morph target
- 교육 서비스 내 재배포가 가능한 라이선스 문서 보관
- 웹 기준 텍스처 1K, Draco/Meshopt 압축 권장, 모델당 10MB 이하 목표

모델을 4~8명으로 늘릴 때는 파일을 코드에 base64로 넣지 말고 오브젝트 스토리지 또는 정적 자산 경로로 관리합니다.
