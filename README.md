# 가족센터 AI 상담 통합 플랫폼 — 실행 가능한 세로 슬라이스

제공된 화면 시안을 하나의 제품 구조로 연결한 프로토타입입니다. 공통 로그인, 역할별 메뉴, 중앙 관리자 대시보드, 상담사 내담자 관리·코파일럿 골격, 그리고 실제 GLB 아바타가 반응하는 페르소나 교육 화면이 포함됩니다.

## 현재 동작하는 범위

- FastAPI 인증 및 역할 권한: `central_admin`, `center_admin`, `counselor`, `trainer`
- 로그인 후 역할별 화면 이동
- 관리자 운영지표 API와 대시보드
- 상담사 내담자 목록·상세·SOAP 구조 화면
- 상담 코파일럿 및 보고서 생성 진입 화면
- 실제 사례관리 DB와 같은 구조의 합성 내담자 4명: 기본정보·가족맥락·FRPS/FSTRESS/BFI-10·누적 회기 기록
- 내담자와 회기를 선택하면 대화 수동 입력 없이 전체 합성 기록을 자동 로드하는 코파일럿 분석 API
- 선택 사례 기반 핵심 이슈·정서·위기 확인·권장 질문·SOAP 초안
- 교육 세션 생성과 SSE 응답 스트리밍
- AI 응답 완료 즉시 감정·비언어 행동을 3D 아바타에 적용
- Rocketbox GLB의 ARKit 계열 표정, 시선 회피, 몸 기울임, 팔짱, 손 비비기
- 내부 TTS가 없을 때 브라우저 한국어 TTS와 립싱크 사용
- 내부망 OpenAI 호환 LLM 및 사내 TTS 교체 어댑터

## 먼저 이해할 실행 구조

Colab과 PowerShell은 서로 다른 역할입니다. 명령을 섞어서 실행하지 않습니다.

```text
Google Colab 브라우저: 믿:음 모델 + 임시 ngrok 주소
Windows PowerShell 1: 로컬 FastAPI 백엔드(8100)
Windows PowerShell 2: Next.js 프론트엔드(3000)
```

- `AI_PROVIDER=mock`으로 화면만 확인할 때는 Colab이 필요 없습니다.
- 실제 믿:음 응답을 사용할 때는 **Colab 준비 → `.env` 수정 → 백엔드 시작/재시작 → 프론트엔드 실행** 순서가 가장 덜 헷갈립니다.
- PowerShell 명령은 Windows PowerShell에서만 실행합니다. Colab 셀에 붙여 넣지 않습니다.
- 설치 명령은 최초 한 번만 실행합니다. 매번 `pip install`이나 `npm install`을 할 필요가 없습니다.

## Windows 최초 1회 설치

PowerShell을 열고 아래 프로젝트 경로로 이동합니다. PowerShell이 `C:\WINDOWS\system32`에서 시작해도 첫 명령으로 위치를 옮기면 됩니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
```

먼저 Python과 Node.js가 Windows에 설치되어 있는지 확인합니다.

```powershell
py -3 --version
node.exe --version
npm.cmd --version
```

- `py -3`에서 `No installed Python found`가 나오면 Python 3.12 x64를 설치합니다. 설치 화면에서 Python Launcher와 PATH 추가를 선택한 뒤 PowerShell을 전부 닫고 새로 엽니다.
- `node.exe` 또는 `npm.cmd`가 없으면 Node.js LTS를 설치한 뒤 PowerShell을 새로 엽니다.
- 이 프로젝트의 복사된 `.venv`가 예전 PC의 Python 경로를 기억하면 `Unable to create process ... Python312` 오류가 날 수 있습니다. 이때는 아래처럼 기존 폴더를 백업 이름으로 옮기고 다시 만듭니다.

```powershell
if (Test-Path -LiteralPath ".venv") {
    Move-Item -LiteralPath ".venv" -Destination ".venv_broken_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}
py -3 -m venv .venv
```

환경 파일과 백엔드 패키지를 준비합니다. `Activate.ps1`은 실행 정책에 걸릴 수 있으므로 사용하지 않습니다.

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements.txt"
```

프론트엔드를 설치합니다. 이 PC에는 `pnpm` 전역 명령이 없을 수 있으므로 기본 절차에서는 `npm.cmd`를 사용합니다.

```powershell
Set-Location -LiteralPath ".\frontend"
npm.cmd install
```

`npm.cmd install`은 최초 한 번, 또는 `package.json`이 바뀐 경우에만 다시 실행합니다.

이미지/PDF OCR까지 사용할 경우 백엔드 기본 패키지 설치 후 다음 선택 패키지를 한 번 추가합니다. OCR을 사용하지 않으면 생략할 수 있습니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements-ocr.txt"
```

자세한 설치·확인 순서는 [`docs/OCR_REPORT_STT.md`](./docs/OCR_REPORT_STT.md)를 참고하세요.

PyTorch 설치 중 `[WinError 206] 파일 이름이나 확장명이 너무 깁니다`가 나오면 같은 명령을 반복하지 마세요. 프로젝트 경로가 긴 경우이므로 [`OCR_REPORT_STT.md`의 WinError 206 절차](./docs/OCR_REPORT_STT.md#winerror-206-파일-이름이나-확장명이-너무-깁니다)에 따라 가상환경만 `%LOCALAPPDATA%\FamilyCenter\venvs\v0_4`에 짧게 다시 만듭니다.

## 평소 실행: PowerShell 2개

### PowerShell 1 — 백엔드

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

이 창은 서버가 실행되는 동안 닫지 않습니다. `http://127.0.0.1:8100/docs`에서 API를 확인할 수 있습니다.

### PowerShell 2 — 프론트엔드

새 PowerShell 창을 하나 더 열고 실행합니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4\frontend"
npm.cmd run dev
```

이 창도 실행 중에는 닫지 않습니다. 브라우저에서 `http://127.0.0.1:3000`을 엽니다.

### 종료와 재시작

- 각 서버 종료: 해당 PowerShell 창에서 `Ctrl+C`
- `.env`를 수정함: 백엔드만 `Ctrl+C` 후 다시 실행
- Colab ngrok URL이 바뀜: `.env`의 주소·키 수정 후 백엔드만 재시작
- 프론트 코드만 수정함: 개발 서버가 대개 자동 반영
- 컴퓨터를 다시 켬: 설치는 생략하고 PowerShell 1과 2의 실행 명령만 수행

## 실제 믿:음까지 연결하는 전체 순서

1. Colab에서 `colab/Midm_Base_OpenAI_Server_Colab.ipynb`을 엽니다.
2. 새 Colab 런타임이면 위에서 아래로 실행해 모델·FastAPI·ngrok을 준비합니다.
3. 같은 런타임에 모델이 이미 로드되어 있으면 모델 로드 셀은 반복하지 않고 서버/ngrok 셀만 필요한 경우 재실행합니다.
4. Colab이 출력한 6개 설정값을 Windows 프로젝트 루트의 `.env`에 반영합니다.
5. PowerShell 1에서 백엔드를 시작하거나 재시작합니다.
6. PowerShell 2에서 프론트엔드를 실행합니다.
7. `http://127.0.0.1:3000/training`에서 `믿:음 연결 정상`을 확인합니다.

Colab의 구체적인 셀 순서와 오류 해결은 [`docs/COLAB_MIDM_DEMO.md`](./docs/COLAB_MIDM_DEMO.md)를 참고하세요.

## `pnpm` 오류 해결

기본 실행에는 `pnpm`이 필요하지 않습니다. 문서대로 `npm.cmd install`, `npm.cmd run dev`를 사용하면 됩니다. `npm` 대신 반드시 pnpm을 쓰고 싶다면 전역 설치 없이 다음처럼 실행할 수 있습니다.

```powershell
npx.cmd --yes pnpm@10 install
npx.cmd --yes pnpm@10 dev
```

Node 설치 여부는 다음으로 확인합니다.

```powershell
node.exe --version
npm.cmd --version
```

둘 중 하나라도 “인식되지 않습니다”가 나오면 Node.js LTS를 설치한 뒤 PowerShell을 완전히 닫았다가 새로 엽니다.

## 자주 보이는 PowerShell 오류

### `No installed Python found`

Windows에 Python 본체가 없고 `py` 실행기만 남아 있는 상태입니다. Python 3.12 x64를 설치하고 새 PowerShell에서 `py -3 --version`이 성공하는지 확인한 뒤 `.venv`를 만듭니다.

### `Unable to create process using ... Python312`

`.venv`가 현재 존재하지 않는 Python 설치 경로를 참조합니다. 위의 `.venv_broken_날짜` 이동 명령으로 보존한 뒤 `py -3 -m venv .venv`를 실행합니다.

### `포트 3000/8100이 이미 사용 중`

대부분 같은 서버를 다른 PowerShell에서 이미 실행 중인 경우입니다. 기존 서버 창에서 `Ctrl+C`로 종료한 후 다시 실행합니다.

프로토타입 계정:

- 상담사: `counselor` / `demo`
- 중앙 관리자: `admin` / `demo`
- 교육 담당자: `trainer` / `demo`

## Docker 실행

`.env`를 만든 후:

```powershell
docker compose up --build
```

## 내부망 연동

`.env`에서 다음 값을 설정합니다.

```text
AI_PROVIDER=internal_openai
INTERNAL_LLM_BASE_URL=http://llm-gateway.internal/v1
INTERNAL_LLM_MODEL=your-model
INTERNAL_LLM_API_KEY=...
INTERNAL_TTS_URL=http://tts.internal/synthesize
AUTH_SECRET=충분히-긴-무작위-비밀값
```

LLM은 OpenAI 호환 `/chat/completions` 응답을 기대합니다. TTS는 `audio_url` JSON을 반환하거나 MP3/WAV 바이너리를 직접 반환할 수 있습니다. 자세한 내용은 `docs/ARCHITECTURE.md`를 참고하세요.

Colab GPU에서 KT 믿:음 `K-intelligence/Midm-2.0-Base-Instruct`를 4-bit로 실행하는 노트북은 `colab/Midm_Base_OpenAI_Server_Colab.ipynb`에 포함되어 있습니다. 전체 연결 순서는 `docs/COLAB_MIDM_DEMO.md`, 운영 전환 방법은 `docs/MIDM_SETUP.md`를 참고하세요. `.env`는 백엔드 시작 시 자동으로 읽으며, 값을 바꾼 뒤에는 FastAPI를 다시 시작해야 합니다. `AI_PROVIDER=mock`이면 화면 검증용 예시 응답이며 실제 생성형 응답이 아닙니다.

기존 Colab 코파일럿의 이미지/PDF OCR, 초기상담기록지·상담기록지·SOAP 통합, 회기·종결 보고서와 교육용 STT를 통합 프론트에 복원했습니다. OCR 선택 설치와 사용법은 `docs/OCR_REPORT_STT.md`를 참고하세요.

## 중요: 운영 전 교체할 항목

현재 로그인 토큰과 메모리 저장소는 로컬 데모용입니다. 운영 환경에서는 공공기관 SSO/OIDC, PostgreSQL, Redis, 감사로그, 비밀관리 시스템으로 교체해야 합니다. 실제 내담자 데이터는 데모에 넣지 마세요. 이 저장소의 페르소나는 실제 인물과 무관한 가상 성인입니다.
