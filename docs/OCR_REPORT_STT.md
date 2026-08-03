# OCR·통합 기록·보고서·STT 사용법

## 코파일럿 화면의 복원된 흐름

상담 코파일럿은 같은 회기 대화와 상담사 메모를 다음 기능에 함께 사용합니다.

1. 믿:음 상담 방향 분석
2. 이미지/PDF 수기 기록 OCR
3. OCR 정제문과 상담사 보완 메모 편집
4. 초기상담기록지·상담기록지·SOAP 3종 통합 초안
5. 근거·확인 필요 항목 검토
6. 회기 요약·중간평가/종결 보고서 생성
7. TXT·JSON 다운로드

AI가 작성한 내용은 자동 확정하지 않습니다. 상담사가 상담 원문, 업로드 원본, 직접 관찰과 기관 양식을 대조한 후 수정·확정해야 합니다.

## OCR 설치

OCR 이외의 기록·보고서 기능은 기본 설치만으로 동작합니다. 이미지/PDF OCR을 사용하려면 프로젝트 루트에서 선택 패키지를 설치하고 백엔드를 재시작합니다.

이 작업에는 Colab, ngrok, `pnpm`, 프론트엔드 재설치가 필요 없습니다. **백엔드가 실행 중인 PowerShell 1에서 `Ctrl+C` → OCR 패키지 설치 → 같은 창에서 백엔드 재실행** 순서로 진행합니다.

### 1. 백엔드 종료

백엔드 로그가 보이는 PowerShell 1을 클릭하고 `Ctrl+C`를 누릅니다.

### 2. 프로젝트 루트에서 OCR 패키지 설치

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements-ocr.txt"
```

EasyOCR가 PyTorch와 OpenCV를 함께 설치하므로 기본 패키지 설치보다 오래 걸리고 용량도 큽니다. 설치가 끝날 때까지 PowerShell을 닫지 않습니다.

### 3. 백엔드 재실행

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

프론트엔드는 재시작하지 않아도 됩니다. 브라우저의 코파일럿 화면을 새로고침하고 OCR 상태가 `사용 가능`으로 바뀌었는지 확인합니다.

첫 OCR 실행 시 EasyOCR 한국어 모델을 추가로 내려받으므로 시간이 걸릴 수 있습니다. 이후에는 캐시를 재사용합니다. 모델 다운로드가 필요한 최초 OCR은 인터넷 연결 상태에서 실행해야 합니다.

### 설치 확인

백엔드를 실행하기 전에 다음 명령으로 필수 모듈을 확인할 수 있습니다.

```powershell
& ".\.venv\Scripts\python.exe" -c "import easyocr, cv2, fitz, PIL; print('OCR 패키지 설치 정상')"
```

`Unable to create process using ... Python312`가 나오면 OCR 문제가 아니라 `.venv`가 깨진 상태입니다. 프로젝트 루트 [`README.md`](../README.md)의 `Unable to create process` 해결 절차로 가상환경을 다시 만든 뒤, 기본 패키지와 OCR 패키지를 차례대로 설치합니다.

### `[WinError 206] 파일 이름이나 확장명이 너무 깁니다`

PyTorch 내부 파일명과 현재 프로젝트 경로를 합친 길이가 Windows 제한을 넘은 것입니다. 이미 설치된 다른 패키지의 문제가 아니며, 같은 긴 `.venv`에서 설치를 반복해도 다시 실패할 가능성이 큽니다.

관리자 권한이나 레지스트리 변경 없이 해결하려면 **가상환경만 짧은 사용자 경로에 새로 생성**합니다. 프로젝트 소스와 `.env`는 현재 위치에 그대로 둡니다.

1. 백엔드 PowerShell에서 `Ctrl+C`를 누릅니다.
2. 프로젝트 루트에서 아래 블록 전체를 차례대로 실행합니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"

$fcVenv = Join-Path $env:LOCALAPPDATA "FamilyCenter\venvs\v0_4"
$fcPython = Join-Path $fcVenv "Scripts\python.exe"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $fcVenv) | Out-Null

if (-not (Test-Path -LiteralPath $fcPython)) {
    & ".\.venv\Scripts\python.exe" -m venv $fcVenv
}

& $fcPython -m pip install --upgrade pip
& $fcPython -m pip install -r ".\backend\requirements-ocr.txt"
& $fcPython -c "import easyocr, cv2, fitz, PIL; print('OCR 패키지 설치 정상')"
```

설치가 끝난 후에는 기존의 긴 `.venv`가 아니라 짧은 가상환경으로 백엔드를 실행합니다.

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
$fcPython = Join-Path $env:LOCALAPPDATA "FamilyCenter\venvs\v0_4\Scripts\python.exe"
& $fcPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

이후 OCR을 사용하는 동안에는 백엔드 실행 명령도 위의 `$fcPython` 버전을 사용합니다. 실패했던 긴 `.venv`는 즉시 삭제할 필요가 없으며, 새 환경이 정상 동작하는 것을 확인한 뒤 별도로 정리할 수 있습니다.

지원 형식과 제한:

- PNG, JPG, JPEG, WEBP, TIF, TIFF, PDF
- 한 번에 최대 5개
- 파일당 기본 12MB
- PDF 기본 12페이지
- 원본, 대비 강화, 문서 강화, 원본+대비 강화

설정값:

```text
OCR_PROVIDER=easyocr
OCR_MAX_FILE_MB=12
OCR_MAX_PDF_PAGES=12
```

OCR 패키지가 없어도 코파일럿의 `OCR 정제 텍스트`에 기존 OCR 결과나 수기 내용을 직접 붙여 넣어 통합 기록과 보고서를 시험할 수 있습니다.

## 교육 화면 STT

현재 프로토타입은 Chrome 또는 Edge의 Web Speech API를 사용합니다. 교육 화면의 `STT` 버튼을 누르고 마이크 권한을 허용하면 상담사 발화 입력란에 중간 인식 결과가 표시됩니다. 다시 누르거나 전송하면 인식을 중지합니다.

```text
STT_PROVIDER=browser
```

브라우저 STT는 브라우저/운영체제 공급자의 온라인 음성인식 서비스를 사용할 수 있으므로 실제 내담자 음성에는 사용하지 않습니다. 시연용 합성 발화만 사용하세요.

내부망 전환 시에는 프론트 구조를 유지하고 설정을 바꿉니다.

```text
STT_PROVIDER=internal_http
INTERNAL_STT_URL=http://stt.internal/transcribe
INTERNAL_STT_API_KEY=...
STT_REQUEST_TIMEOUT=120
```

백엔드에는 `GET /api/v1/speech/status`와 `POST /api/v1/speech/transcribe` 경계를 마련했습니다. 내부 STT 응답은 `{ "text": "..." }` 또는 `{ "transcript": "..." }` 형식을 사용합니다. 실제 내부 STT 연결 시 프론트의 MediaRecorder 업로드 모드만 추가하면 됩니다.

## 운영 전환 전 확인

- 실제 상담 DB와 업로드 파일은 내부망 저장소 사용
- 파일 악성코드 검사와 보존기간 정책 추가
- OCR 원본·정제문·상담사 수정본의 변경 이력 저장
- 보고서 생성·수정·확정자 감사로그
- 브라우저 STT 제거 후 내부 STT 또는 온프레미스 Whisper 계열로 교체
- AI 초안과 상담사 확정본을 데이터 모델에서 명확히 분리
