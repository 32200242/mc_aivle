# KT 믿:음(Mi:dm) 연결 방법

현재 플랫폼은 화면 코드와 모델 실행 코드를 분리합니다. 프론트엔드는 항상 로컬 FastAPI만 호출하고, FastAPI가 설정에 따라 데모 응답 또는 믿:음 서버를 호출합니다.

```text
브라우저(Next.js) → 로컬 FastAPI :8100 → 믿:음 OpenAI 호환 API
```

## 시연용: Colab GPU의 Base 모델

프로젝트에 포함된 [`colab/Midm_Base_OpenAI_Server_Colab.ipynb`](../colab/Midm_Base_OpenAI_Server_Colab.ipynb)을 Google Colab에 업로드해 위에서 아래로 실행합니다. **Colab 모델 준비 → Windows `.env` 수정 → PowerShell 백엔드 재시작 → 프론트 실행** 순서와 `pnpm` 없는 실행법은 [`COLAB_MIDM_DEMO.md`](./COLAB_MIDM_DEMO.md)에 있습니다.

Colab 마지막 셀이 출력하는 값을 프로젝트 루트 `.env`에 넣습니다.

```text
AI_PROVIDER=internal_openai
INTERNAL_LLM_BASE_URL=https://임시주소.ngrok-free.app/v1
INTERNAL_LLM_MODEL=K-intelligence/Midm-2.0-Base-Instruct
INTERNAL_LLM_API_KEY=Colab이_출력한_키
LLM_REQUEST_TIMEOUT=240
LLM_HEALTH_TIMEOUT=12
```

`.env`는 백엔드 시작 시 자동으로 읽습니다. 값을 바꾼 뒤에는 반드시 FastAPI를 종료하고 다시 실행해야 합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100
```

교육·코파일럿 화면 상단의 상태는 이제 설정 여부뿐 아니라 Colab의 `/v1/models` 실응답까지 확인합니다.

- `믿:음 연결 정상`: 모델 API에 도달함
- `믿:음 서버 오프라인`: Colab 런타임, 서버 셀, ngrok 터널 또는 URL 확인 필요
- `데모 응답`: `.env`가 `AI_PROVIDER=mock`이거나 백엔드를 재시작하지 않음

## 내부망/운영용: 고정 GPU 서버

운영에서는 Colab과 ngrok을 제거하고 Linux CUDA 서버에서 vLLM 등 OpenAI 호환 서버를 고정 주소로 운영하는 구성이 적합합니다.

```bash
pip install "vllm>=0.8"
vllm serve K-intelligence/Midm-2.0-Base-Instruct --host 0.0.0.0 --port 8000 --api-key YOUR_INTERNAL_KEY
```

플랫폼 `.env`에서 주소만 교체합니다. 프론트·백엔드 API 계약은 바뀌지 않습니다.

```text
AI_PROVIDER=internal_openai
INTERNAL_LLM_BASE_URL=http://llm-gateway.internal:8000/v1
INTERNAL_LLM_MODEL=K-intelligence/Midm-2.0-Base-Instruct
INTERNAL_LLM_API_KEY=YOUR_INTERNAL_KEY
```

운영 전환 시에는 고정 GPU VM 또는 온프레미스 GPU, VPN/VPC, TLS, 비밀관리, 요청 감사로그, 비식별화, 동시요청 제한을 추가해야 합니다. 상담 원문 DB는 내부망에 두고 모델에는 필요한 최소 비식별 텍스트만 전달하는 구조를 권장합니다.

## 선택 사항: FastAPI 프로세스에서 직접 로드

별도 Linux GPU 환경에서는 다음 패키지를 설치하고 `AI_PROVIDER=midm_local`을 사용할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-midm.txt
```

```text
AI_PROVIDER=midm_local
MIDM_MODEL_ID=K-intelligence/Midm-2.0-Base-Instruct
MIDM_HF_TOKEN=
MIDM_USE_4BIT=true
```

일반 Windows PC에서는 Base 4-bit CUDA 경로가 불안정하고 백엔드와 모델이 한 프로세스에 결합되므로, 현재 시연에도 `internal_openai` 방식이 더 적합합니다.

## 모드 구분

- `AI_PROVIDER=mock`: 모델을 쓰지 않는 화면 검증용 규칙 기반 응답
- `AI_PROVIDER=internal_openai`: Colab, vLLM, 사내 모델 게이트웨이 호출
- `AI_PROVIDER=midm_local`: FastAPI가 Hugging Face 모델을 직접 로드

실제 공급자에서 오류가 나면 mock으로 몰래 대체하지 않습니다. 화면에 연결 또는 JSON 해석 오류를 표시해 시연 중 원인을 구분할 수 있게 했습니다.

공식 모델 카드: https://huggingface.co/K-intelligence/Midm-2.0-Base-Instruct
