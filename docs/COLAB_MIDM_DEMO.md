# Colab 믿:음 Base + PaddleOCR-VL 시연 절차

## 준비물

1. Google Colab을 사용할 Google 계정
2. 무료 ngrok 계정과 authtoken
3. 이 프로젝트의 `colab/Midm_Base_OpenAI_Server_Colab.ipynb`
4. 합성된 가상 내담자 문장만 사용한다는 시연 원칙

Hugging Face 모델은 공개되어 있어 `HF_TOKEN`이 없어도 받을 수 있습니다. 다운로드 제한이 발생하는 경우에만 Read 권한 토큰을 Colab Secret에 추가합니다.

## 전체 순서 한눈에 보기

```text
최초 설치: Windows에서 백엔드/프론트 의존성 설치(한 번만)
시연 시작: Colab 모델 서버 준비
연결 설정: Colab이 출력한 믿:음·OCR 값을 Windows .env에 복사
로컬 실행: PowerShell 1 백엔드 → PowerShell 2 프론트엔드
```

Colab은 믿:음 모델을 실행하는 곳이고, PowerShell은 로컬 웹서비스를 실행하는 곳입니다. Colab 셀에 PowerShell 명령을 넣거나 PowerShell에 Colab Python 코드를 넣지 않습니다.

PaddleOCR-VL 1.6은 Transformers 5 전용 가상환경·별도 프로세스에서 실행되므로 Transformers 4.x를 사용하는 믿:음 환경을 덮어쓰지 않습니다. 두 프로세스는 같은 GPU를 공유하되 공용 잠금으로 한 번에 하나만 추론합니다.

## A. Colab에서 모델 서버 열기

1. Google Colab에서 `파일 > 노트 업로드`를 누릅니다.
2. `Midm_Base_OpenAI_Server_Colab.ipynb`을 선택합니다.
3. `런타임 > 런타임 유형 변경 > T4 GPU` 이상을 선택합니다.
4. 왼쪽 열쇠 아이콘에서 Secret을 만듭니다.
   - 이름: `NGROK_AUTHTOKEN`
   - 값: ngrok 대시보드의 authtoken
   - `노트북 액세스`를 켭니다.
5. 필요할 때만 `HF_TOKEN`을 같은 방법으로 추가합니다.
6. 새 런타임이면 1번 셀부터 순서대로 실행합니다.
7. 모델 로드 완료 후 로컬 API 테스트 응답을 확인합니다.
8. PaddleOCR-VL 격리 사이드카와 OCR 프록시 셀까지 실행합니다.
9. 마지막 셀의 `.env` 값을 복사하고 `외부 PaddleOCR 상태 정상`을 확인합니다.

T4에서 첫 설치·다운로드·로드는 보통 가장 오래 걸립니다. 한 번 로드된 뒤의 첫 생성도 CUDA 초기화 때문에 느리고, 두 번째부터 상대적으로 빨라집니다.

같은 Colab 런타임에서 다시 실행할 때는 다음처럼 구분합니다.

- 모델이 메모리에 남아 있음: 무거운 모델 로드 셀은 다시 실행하지 않음
- FastAPI만 멈춤: FastAPI 서버 셀부터 다시 실행
- ngrok 주소만 만료됨: ngrok 셀과 외부 테스트 셀만 다시 실행
- 런타임이 초기화되었거나 GPU가 바뀜: 처음부터 다시 실행

## B. Windows 프로젝트에 연결

Windows 최초 설치와 Python/Node 확인은 프로젝트 루트 [`README.md`](../README.md)의 `Windows 최초 1회 설치`를 먼저 따릅니다. 현재 복사본의 `.venv`가 예전 Python 경로를 가리키면 README의 가상환경 재생성 절차를 적용합니다.

현재 프로젝트 루트:

```text
C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4
```

PowerShell에서 다음을 실행합니다. PowerShell이 `C:\WINDOWS\system32`에서 열렸더라도 이 명령으로 정확한 프로젝트 폴더로 이동합니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
notepad .env
```

Colab이 출력한 아래 키들을 기존 `.env`에서 찾아 값을 교체합니다. 같은 키를 두 줄로 만들지 마세요.

```text
AI_PROVIDER=internal_openai
INTERNAL_LLM_BASE_URL=https://실제주소.ngrok-free.app/v1
INTERNAL_LLM_MODEL=K-intelligence/Midm-2.0-Base-Instruct
INTERNAL_LLM_API_KEY=실제키
LLM_REQUEST_TIMEOUT=240
LLM_HEALTH_TIMEOUT=12
OCR_PROVIDER=paddleocr_vl_http
INTERNAL_OCR_URL=https://실제주소.ngrok-free.app/v1/ocr
INTERNAL_OCR_API_KEY=실제키
OCR_REQUEST_TIMEOUT=300
OCR_HEALTH_TIMEOUT=12
OCR_REMOTE_BATCH_SIZE=4
```

백엔드용 PowerShell 1에서 `Ctrl+C`로 기존 프로세스를 종료한 뒤, 프로젝트 루트에서 실행합니다. Python 가상환경을 활성화할 필요는 없습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100
```

`python-dotenv`가 추가되어 이 명령만으로 프로젝트 루트 `.env`를 자동으로 읽습니다.

프론트엔드가 아직 실행 중이 아니면 새 PowerShell 2에서 실행합니다. `pnpm` 대신 Windows에 기본 설치된 `npm.cmd`를 사용합니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4\frontend"
npm.cmd run dev
```

처음 한 번도 프론트 의존성을 설치하지 않았다면 `npm.cmd install`을 먼저 한 번만 실행합니다. 평소에는 `npm.cmd run dev`만 실행합니다.

브라우저를 새로고침하고 다음 중 하나로 확인합니다.

- 교육 영상: `http://127.0.0.1:3000/training` — Colab 없이도 재생
- 상담 코파일럿: 로그인 후 왼쪽 `상담 코파일럿`

상담 코파일럿에서 `믿:음 연결 정상`을 확인하고 기록 영역에서 `PaddleOCR-VL 1.6 준비됨`이 보이면 연결이 끝난 것입니다.

## C. 시연 당일 권장 순서

1. Colab 런타임 연결
2. 새 런타임이면 전체 셀 실행, 기존 런타임이면 필요한 서버/ngrok 셀만 실행
3. Colab 로컬 API 테스트와 마지막 외부 테스트 성공 확인
4. 새 ngrok URL과 API 키를 Windows `.env`에 반영
5. PowerShell 1에서 로컬 백엔드 시작 또는 재시작
6. PowerShell 2에서 `npm.cmd run dev`로 프론트엔드 실행
7. 교육 영상 재생 확인
8. 상담 코파일럿에서 믿:음 질문 1회, OCR 합성 문서 1장으로 각각 워밍업
9. 본 시연 시작

Colab은 런타임이 종료되거나 재연결될 수 있습니다. 시연 20~30분 전에 켜고, 노트북 탭을 열어 둔 상태에서 사용하세요. 인위적인 keep-alive 코드는 넣지 않았습니다.

## 오류별 해결

### `python -m venv ... returned non-zero exit status 1`

Colab Python 3.12 이미지에 `ensurepip/python3-venv`가 빠져 발생하는 환경 오류입니다. 수정된 OCR 셀은 표준 `venv` 대신 `virtualenv`를 설치해 사용하고, 실패하면서 만들어진 `/content/paddleocr_vl_env`만 다시 생성합니다. 런타임 재시작이나 Mi:dm 재로딩 없이 수정된 9번 OCR 셀부터 다시 실행하면 됩니다.

### 화면에 계속 `데모 응답`이 보임

- `.env`의 `AI_PROVIDER=internal_openai` 확인
- `.env`가 `frontend` 폴더가 아니라 프로젝트 루트에 있는지 확인
- 백엔드를 `Ctrl+C` 후 재시작했는지 확인
- 백엔드 시작 로그가 새 프로세스인지 확인

### `믿:음 서버 오프라인`

- Colab 마지막 외부 테스트 셀을 다시 실행
- Colab 런타임이 연결 상태인지 확인
- 서버 시작 셀과 ngrok 셀을 다시 실행
- 재실행으로 URL이 바뀌었다면 `.env` 갱신 후 백엔드 재시작
- `INTERNAL_LLM_API_KEY`가 Colab 출력과 한 글자도 다르지 않은지 확인

### HTTP 401

`INTERNAL_LLM_API_KEY` 불일치입니다. Colab ngrok 셀의 현재 출력값을 다시 복사합니다.

### HTTP 400 · 입력 토큰 초과

코파일럿에 넣은 대화 원문을 줄입니다. 노트북 시연 서버는 T4 안정성을 위해 입력 6,144토큰, 출력 1,600토큰으로 제한합니다.

HTTP 400의 원인이 화면에 보이지 않으면 Colab 로컬 API 테스트 셀에서 `response.raise_for_status()` 전에 다음 두 줄을 임시로 넣어 실제 오류를 확인합니다.

```python
print("STATUS:", response.status_code)
print("BODY:", response.text)
```

수정본 노트북은 400일 때 오류 본문을 자동으로 표시합니다. `token_type_ids` 오류가 다시 보이면 예전 FastAPI 서버가 남은 경우이므로 모델을 다시 로드하지 말고 FastAPI 서버 셀을 다시 실행합니다.

### PowerShell에서 `pnpm`을 인식하지 못함

이 프로젝트는 pnpm 전역 설치 없이 실행할 수 있습니다. 프론트 폴더에서 다음을 사용합니다.

```powershell
npm.cmd install   # 최초 한 번만
npm.cmd run dev   # 평소 실행
```

pnpm을 꼭 사용하려면 `pnpm` 대신 `npx.cmd --yes pnpm@10`을 붙입니다.

```powershell
npx.cmd --yes pnpm@10 install
npx.cmd --yes pnpm@10 dev
```

### CUDA out of memory

1. 다른 모델·노트북이 같은 런타임에 로드되어 있지 않은지 확인합니다.
2. `런타임 > 세션 다시 시작` 후 이 노트북만 실행합니다.
3. 계속 실패하면 L4 또는 A100 런타임을 선택합니다.
4. 동시 요청을 보내지 않습니다. 노트북 서버는 기본적으로 한 번에 한 생성만 처리합니다.

### 응답이 너무 느림

- 첫 요청은 워밍업이라 더 느립니다. 짧은 질문으로 한 번 생성한 뒤 시연합니다.
- T4에서는 긴 코파일럿 JSON이 교육 내담자 한두 문장보다 오래 걸립니다.
- `max_tokens`는 백엔드 요청별로 이미 제한되어 있습니다.
- 시연 단계에서 동시 사용자 수는 1명으로 유지합니다.

## 데이터와 보안 경계

이 구성은 Colab과 ngrok을 경유하므로 실제 내담자 데이터 처리용이 아닙니다. 이름, 연락처, 주소, 기관 내부 식별자, 실제 상담 원문을 보내지 말고 가명·합성 문장만 사용하세요. API 키는 인증 없는 공개 호출을 막지만 운영 수준의 내부망 통제나 개인정보 보호를 대신하지 않습니다.

운영 전환 시에는 `INTERNAL_LLM_BASE_URL`을 고정 사내/VPC GPU 서버 주소로 바꾸면 됩니다. 프론트엔드와 코파일럿/교육 API 구조는 그대로 유지됩니다.
