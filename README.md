# 가족센터 AI 상담 통합 플랫폼

가족센터의 운영 분석, 상담 사례 관리, AI 상담기록 지원, 상담자 교육을 하나의 웹 애플리케이션으로
연결한 참조 구현이다. FastAPI 백엔드와 Next.js 프런트엔드, 내부망 AI 어댑터, 선택적 GPU
서비스, Docker·클라우드 배포 구성을 포함한다.

- 시스템 구성: [`docs/PROJECT_STRUCTURE.md`](./docs/PROJECT_STRUCTURE.md)
- 데이터 정의와 거버넌스: [`docs/DATA_CATALOG.md`](./docs/DATA_CATALOG.md)
- 데이터·척도 이용 안내: [이 문서 하단](#데이터척도-이용-안내)

## 가장 간단한 외부 화면 시연

Docker Desktop을 켠 뒤 저장소 루트의 `start-public-demo.cmd`를 더블클릭하면 API, 화면, 무료 Cloudflare Quick Tunnel이 함께 실행된다. 표시되는 `https://...trycloudflare.com` 주소를 다른 사람에게 공유하면 된다. 계정과 카드가 필요 없지만 PC와 실행 창을 켜 두어야 하고, 다시 실행할 때마다 주소가 변경된다. 자세한 내용은 [`deploy/quick-tunnel/README.md`](./deploy/quick-tunnel/README.md)를 참고한다.

제공된 화면 시안을 하나의 제품 구조로 연결한 프로토타입이다. 공통 로그인, 역할별 메뉴, 중앙 관리자 대시보드, 상담사 내담자 관리·Mi:dm 코파일럿, 그리고 가상 내담자 상담사 교육 실습 화면이 포함된다.

## 현재 동작하는 범위

- FastAPI 인증 및 역할 권한: `central_admin`, `counselor`
- 로그인 후 역할별 화면 이동
- 관리자 운영지표 API와 대시보드
- 상담사 내담자 목록·상세·SOAP 구조 화면
- 상담 코파일럿 및 보고서 생성 진입 화면
- 상담인력 1,724명과 내담자 14,143명의 고정 배정 데이터: 기본정보·74개 문항 원 응답·계산 점수·누적 회기 기록
- 내담자와 회기를 선택하면 대화 수동 입력 없이 전체 합성 기록을 자동 로드하는 코파일럿 분석 API
- 선택 사례 기반 핵심 이슈·정서·위기 확인·권장 질문·SOAP 초안
- 교육 탭은 대화·비언어 행동·슈퍼바이저 피드백·STT 흐름을 유지하며, 첫 고정 응답은 사전 제작 MP4로 즉시 재생하고 이후 턴은 믿:음·TTS·표현 서비스로 이어짐
- 이미지/PDF OCR은 PaddleOCR-VL 1.6을 사용하고, 원본 대조·수정 확인 없이는 기록 초안을 생성하지 못하도록 차단
- 내부망 OpenAI 호환 LLM 및 사내 TTS 교체 어댑터
- 17개 시·도 → 244개 기관 → 상담인력 1,724명 → 내담자군 → 760일 운영지표 연결 데이터
- 지역·센터 클릭형 관리자 대시보드와 시간순 검증 기반 28일 상담수요 예측

## 초기 환경 구성

소스 코드와 고정 검증 자산은 포함되어 있으며, 비밀값·설치 결과·대용량 런타임 데이터·외부 AI
모델은 실행환경에서 별도로 구성한다. 로컬 환경에서는 다음 두 항목을 먼저 준비한다.

1. `.env.example`을 복사해 로컬 전용 `.env`를 만든다.
2. 상담 데이터베이스 `backend/data/counseling_demo_v3.sqlite3`을 생성하거나, 별도 데이터
   자산의 `counseling/counseling_demo_v3.sqlite3`을 같은 경로에 배치한다.

소스 코드와 런타임 데이터는 별도 배포 단위로 제공한다. 데이터 ZIP을 해제한 뒤
`family_center_data/실제사용_데이터셋/counseling/counseling_demo_v3.sqlite3`을 소스의
`backend/data/counseling_demo_v3.sqlite3`에 배치하거나, 프로젝트 루트 `.env`의
`COUNSELING_DATA_PATH`에 해당 SQLite 파일의 절대경로를 지정한다.

### 외부 준비 항목

| 항목 | 관리 원칙 | 준비 사항 |
|---|---|---|
| `.env`, `.env.local` 등 실제 환경파일 | API 키와 비밀값 보호 | `.env.example`을 `.env`로 복사하고 필요한 값만 입력 |
| `backend/data/counseling_demo_v3.sqlite3` | 대용량 런타임 데이터는 별도 데이터 자산으로 관리 | 아래 생성 스크립트를 실행하거나, 데이터 자산의 v3 DB를 배치하거나, 별도 DB 경로를 `COUNSELING_DATA_PATH`에 지정 |
| `backend/data/training_progress.json` | 사용자별 실행 상태인 런타임 파일 | 별도 준비 불필요. 교육 API 사용 시 자동 생성 |
| `.venv`, `node_modules`, `.pnpm-store`, npm 캐시 | OS·PC별 설치 결과 | Python 및 프론트엔드 의존성을 각 PC에서 설치 |
| Mi:dm, PaddleOCR-VL, LongCat 모델 가중치 | 용량·라이선스·GPU 실행환경이 저장소 밖에 있음 | 해당 Colab 노트북 또는 사내 추론 서버 준비 |
| API 키, Hugging Face 토큰, ngrok 토큰 | 비밀정보 | Colab Secrets 또는 로컬 `.env`에만 저장하고 Git에 커밋하지 않음 |
| 테스트 임시폴더, 빌드 결과, 검증 캡처 | 재생성 가능한 산출물 | 필요할 때 테스트·빌드·검증 절차로 다시 생성 |

대시보드용 합성 CSV, 데모 음성·영상, 인물 이미지, 지도 SVG, 프론트 정적 자산은 저장소에 포함되어 있다.

### 최소 로컬 실행 준비

프로젝트 루트에서 PowerShell로 다음을 최초 한 번 실행한다. DB는 고정 시드로 재현 가능하게 생성되며 실제 내담자 데이터를 사용하거나 외부 LLM을 호출하지 않는다.

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

py -3 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements.txt"
& ".\.venv\Scripts\python.exe" ".\backend\scripts\build_counseling_dataset.py" --anchor-date 2026-08-10

Set-Location -LiteralPath ".\frontend"
npm.cmd install
Set-Location -LiteralPath ".."
```

DB 생성 후 아래 명령이 `True`를 출력하면 상담사–내담자 기능을 실행할 준비가 된 것이다.

```powershell
Test-Path -LiteralPath ".\backend\data\counseling_demo_v3.sqlite3"
```

화면과 고정 데모만 확인하려면 `.env`의 `AI_PROVIDER=mock`, `AVATAR_PROVIDER=static_2d`를 유지하면 된다. 이 기본 로컬 시연은 별도 GPU 없이 결정론적으로 동작한다. 실제 생성형 AI·OCR·음성·영상 기능은 Colab 또는 기관 GPU 서버를 연결할 때 활성화된다. 연결 확장은 프로젝트 루트 `.env`에서 제공자, 엔드포인트와 인증 값을 설정한 뒤 백엔드를 재시작하면 적용된다.

### 기능별로 추가해야 하는 것

| 사용할 기능 | 추가 준비 | 관련 설정·문서 |
|---|---|---|
| 관리자 대시보드·수요예측 | 기본 설치만 필요. XGBoost는 선택 사항이며 미설치 시 내장 엔진 사용 | `backend/requirements-forecast.txt`, [`docs/DASHBOARD_DATA_MODEL.md`](./docs/DASHBOARD_DATA_MODEL.md) |
| 실제 Mi:dm 응답 | GPU Colab 또는 OpenAI 호환 사내 서버, 서버 URL·모델명·API 키 | `AI_PROVIDER=internal_openai`, `INTERNAL_LLM_*`, [`docs/COLAB_MIDM_DEMO.md`](./docs/COLAB_MIDM_DEMO.md) |
| 이미지/PDF OCR | 로컬 전처리 패키지와 PaddleOCR-VL 원격 서버 | `backend/requirements-ocr.txt`, `INTERNAL_OCR_*`, [`docs/OCR_REPORT_STT.md`](./docs/OCR_REPORT_STT.md) |
| 음성 합성·음성 인식 | 호환 TTS/STT 서버의 URL과 선택적 API 키 | `INTERNAL_TTS_*`, `INTERNAL_STT_*` |
| 정적 교육 영상·2D 아바타 | 추가 준비 없음. 필요한 MP4·이미지가 저장소에 포함됨 | `AVATAR_PROVIDER=static_2d` |
| LongCat 생성 영상 | Mi:dm/OCR과 분리된 전용 GPU, LongCat 코드·가중치, 워커 URL·공유 키 | `AVATAR_PROVIDER=longcat_http`, `LONGCAT_AVATAR_*`, [`workers/longcat_avatar/README.md`](./workers/longcat_avatar/README.md) |
| Docker 실행 | Docker Desktop, `.env`, 미리 생성한 상담 SQLite | 아래 `Docker 실행` 절 참고 |

실제 AI 기능을 켤 때에도 비밀값은 README나 노트북 출력에 저장하지 말고 `.env` 또는 Colab Secrets에만 둔다. 배포 전에는 최소한 `AUTH_SECRET`을 충분히 긴 무작위 값으로 교체해야 한다.

## 연결형 관리자 데이터와 예측

관리자 대시보드(`/admin/dashboard`)의 지도와 센터 목록을 누르면 같은 데이터에서 조회 범위가 바뀐다. 상담수요 전망(`/admin/analytics`)은 28일짜리 rolling-origin 검증창 3개에서 Ridge·Boost·계절 기준선을 비교·앙상블하고, 결과를 상담 슬롯 처리용량에 연결해 M/M/c(Erlang-C) 기반 예약 대기압력을 계산한다. 여기서 대기는 상담실 앞의 현장 대기가 아니라, 예약을 요청했지만 아직 상담 슬롯이 배정되지 않은 수요의 운영상 집계이다. 변수 대응, 계산식, 가정, 적용 한계와 연구 근거는 [`docs/DASHBOARD_DATA_MODEL.md`](./docs/DASHBOARD_DATA_MODEL.md)에 정리했다.

2026년 공식 참고 목표는 가족상담 서비스 이용자 304,699건, 이용자 만족도 93.0점이다. 그래프의 초록 점선은 연간 목표를 12개월로 환산하고, 지역·센터에서는 최근 상담 접촉 비중으로 배분한 운영 참고선이며 센터별 평가 할당량이 아니다. 상담 접촉과 수요 전망 그래프는 일별 원자료를 월별로 합산해 Y축 값과 `건/월` 단위로 표시한다.

## 상담 코파일럿 회기 흐름

코파일럿은 회기 번호를 자유롭게 건너뛰지 않는다. 신규 사례의 1회기 준비에는 사전문진만 사용하고, 실제 1회기 후 `초기상담기록지`를 확정해야 2회기가 열린다. 이미 2·3·4회기인 기존 사례는 현재 회기 이전 기록을 완료 상태로 불러오고 현재 회기의 `상담기록지`만 작성 가능하게 연다. 2회기부터는 해당 회기의 `상담기록지`를 확정해야 다음 회기가 열린다. SOAP/OCR은 선택 참고자료이고, 업로드만으로 회기가 완료되지는 않는다. 작성 중 초안은 다음 회기 AI 분석에서 제외하며 확정된 기록만 누적한다.

배분 근거, 테이블 관계, 재생성 명령, 실제 DB 교체 지점은 [`docs/DASHBOARD_DATA_MODEL.md`](./docs/DASHBOARD_DATA_MODEL.md)에 정리했다. 생성된 데이터 파일은 `backend/data/dashboard_demo/`에 있으며 실제 사람이나 실제 기관 실적을 포함하지 않는다.

## 상담사–내담자 연결 데이터

`backend/data/counseling_demo_v3.sqlite3`은 상담사별 활성 사례 합계 14,143건을 배정 관계로 펼친 고정 시드 합성 데이터이다. 이 파일은 별도 데이터 자산으로 관리하므로 초기 환경에서는 아래 명령으로 생성하거나 제공된 데이터베이스를 배치한다. 사례마다 가족관계 문제징후 18문항, 가족스트레스 45문항, BFI-10 10문항, 관계 해체 고려 1문항의 원 응답과 코드로 계산한 점수, 회기 기록 4건을 연결한다. 가족관계 문제징후는 18~90점 원점수와 확인 기준 54점을 사용하고, 가족스트레스는 경험빈도 0~45건과 부담 합계 0~225점을 분리한다. 웹 요청 중에는 데이터를 생성하거나 LLM을 호출하지 않고 필요한 상담사의 한 페이지와 선택 사례만 조회한다.

고정 데이터 파일을 다시 만들 때만 아래 명령을 실행한다.

```powershell
& ".\.venv\Scripts\python.exe" backend\scripts\build_counseling_dataset.py --anchor-date 2026-08-10
```

기존 배정·일정·회기 데이터를 유지한 채 설문 응답과 점수만 갱신하려면 다음 명령을 사용한다.

```powershell
& ".\.venv\Scripts\python.exe" backend\scripts\migrate_questionnaire_scoring.py
```

합성 상담 일정은 위 기준일과의 간격을 보존한 채 한국시간 서비스 당일에 맞춰 자동 이동하므로, 다음 날 접속해도 지난 일정이 `다음 상담`으로 표시되지 않는다. 테스트나 고정 시연 날짜가 필요하면 `SERVICE_DATE=YYYY-MM-DD`를 설정할 수 있다.

별도 위치의 데이터 파일을 사용하려면 `COUNSELING_DATA_PATH` 환경변수에 SQLite 파일 경로를 지정한다. 향후 PostgreSQL로 전환할 때는 `clients`, `counselor_client_assignments`, `questionnaire_items`, `questionnaire_responses`, `assessment_scores`, `counseling_sessions` 테이블을 같은 관계로 이전하면 된다.

## 먼저 이해할 실행 구조

Colab과 PowerShell은 서로 다른 역할이다. 명령을 섞어서 실행하지 않는다.

```text
Google Colab GPU: 믿:음 + 격리된 PaddleOCR-VL 1.6 + 임시 ngrok 주소
Windows PowerShell 1: 로컬 FastAPI 백엔드(8100)
Windows PowerShell 2: Next.js 프론트엔드(3000)
```

- `AI_PROVIDER=mock`으로 화면만 확인할 때는 Colab이 필요 없다.
- 실제 믿:음 응답을 사용할 때는 **Colab 준비 → `.env` 수정 → 백엔드 시작/재시작 → 프론트엔드 실행** 순서가 가장 덜 헷갈린다.
- PowerShell 명령은 Windows PowerShell에서만 실행한다. Colab 셀에 붙여 넣지 않는다.
- 설치 명령은 최초 한 번만 실행한다. 매번 `pip install`이나 `npm install`을 할 필요가 없다.

## Windows 최초 1회 설치

PowerShell을 열고 아래 프로젝트 경로로 이동한다. PowerShell이 `C:\WINDOWS\system32`에서 시작해도 첫 명령으로 위치를 옮기면 된다.

```powershell
Set-Location -LiteralPath "C:\path\to\family_center_final"
```

먼저 Python과 Node.js가 Windows에 설치되어 있는지 확인한다.

```powershell
py -3 --version
node.exe --version
npm.cmd --version
```

- `py -3`에서 `No installed Python found`가 나오면 Python 3.12 x64를 설치한다. 설치 화면에서 Python Launcher와 PATH 추가를 선택한 뒤 PowerShell을 전부 닫고 새로 연다.
- `node.exe` 또는 `npm.cmd`가 없으면 Node.js LTS를 설치한 뒤 PowerShell을 새로 연다.
- 기존 `.venv`가 현재 시스템과 다른 Python 경로를 참조하면 `Unable to create process ... Python312` 오류가 날 수 있다. 이때는 아래처럼 기존 폴더를 백업 이름으로 옮기고 다시 만든다.

```powershell
if (Test-Path -LiteralPath ".venv") {
    Move-Item -LiteralPath ".venv" -Destination ".venv_broken_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}
py -3 -m venv .venv
```

환경 파일과 백엔드 패키지를 준비한다. `Activate.ps1`은 실행 정책에 걸릴 수 있으므로 사용하지 않는다.

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

프론트엔드를 설치한다. 이 PC에는 `pnpm` 전역 명령이 없을 수 있으므로 기본 절차에서는 `npm.cmd`를 사용한다.

```powershell
Set-Location -LiteralPath ".\frontend"
npm.cmd install
```

`npm.cmd install`은 최초 한 번, 또는 `package.json`이 바뀐 경우에만 다시 실행한다.

이미지/PDF OCR까지 사용할 경우 로컬 백엔드에는 PDF·이미지 전처리 패키지만 추가한다. PaddleOCR-VL 1.6 모델 자체는 Colab GPU에서 실행된다.

```powershell
Set-Location -LiteralPath "C:\path\to\family_center_final"
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements-ocr.txt"
```

자세한 설치·확인 순서는 [`docs/OCR_REPORT_STT.md`](./docs/OCR_REPORT_STT.md)를 참고한다.

상담 수요 전망은 추가 설치 없이 내장 Gradient Boosting으로 동작한다. 실제 서버나 Colab에서 XGBoost 엔진을 사용하려면 다음 선택 패키지를 최초 한 번 설치한다. 설치 후 백엔드를 다시 시작하면 자동으로 XGBoost를 사용하며, 프론트엔드 코드는 바꿀 필요가 없다.

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements-forecast.txt"
```

내부망 배포에서는 인터넷 설치 대신 동일 버전의 wheel 파일을 사내 패키지 저장소에 보관한다. 설치 여부와 관계없이 Ridge·Boost·계절 기준선의 시계열 검증 앙상블 계약은 동일하다.

## 평소 실행: PowerShell 2개

### PowerShell 1 — 백엔드

```powershell
Set-Location -LiteralPath "C:\path\to\family_center_final"
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

이 창은 서버가 실행되는 동안 닫지 않는다. `http://127.0.0.1:8100/docs`에서 API를 확인할 수 있다.

### PowerShell 2 — 프론트엔드

새 PowerShell 창을 하나 더 열고 실행한다.

```powershell
Set-Location -LiteralPath "C:\path\to\family_center_final\frontend"
npm.cmd run dev
```

이 창도 실행 중에는 닫지 않는다. 브라우저에서 `http://127.0.0.1:3000`을 연다.

### 종료와 재시작

- 각 서버 종료: 해당 PowerShell 창에서 `Ctrl+C`
- `.env`를 수정함: 백엔드만 `Ctrl+C` 후 다시 실행
- Colab ngrok URL이 바뀜: `.env`의 주소·키 수정 후 백엔드만 재시작
- 프론트 코드만 수정함: 개발 서버가 대개 자동 반영
- 컴퓨터를 다시 켬: 설치는 생략하고 PowerShell 1과 2의 실행 명령만 수행

## 실제 믿:음까지 연결하는 전체 순서

1. Colab에서 `colab/Midm_Base_OpenAI_Server_Colab.ipynb`을 연다.
2. 새 GPU 런타임이면 위에서 아래로 실행해 믿:음·PaddleOCR-VL 사이드카·FastAPI·ngrok을 준비한다.
3. 같은 런타임에 모델이 이미 로드되어 있으면 모델 로드 셀은 반복하지 않고 서버/ngrok 셀만 필요한 경우 재실행한다.
4. Colab의 마지막 셀이 출력한 `.env` 블록 전체를 Windows 프로젝트 루트의 `.env`에 반영한다.
5. PowerShell 1에서 백엔드를 시작하거나 재시작한다.
6. PowerShell 2에서 프론트엔드를 실행한다.
7. `http://127.0.0.1:3000/training`에서 완성 교육 영상이 재생되는지 확인한다. Mi:dm 연결은 `/counselor/copilot`에서 확인한다.

구체적인 Colab 셀 순서와 오류 해결은 [`docs/COLAB_MIDM_DEMO.md`](./docs/COLAB_MIDM_DEMO.md)를 참고한다. 교육 탭은 정적 MP4이므로 Colab 연결 여부와 무관하게 재생된다.

## `pnpm` 오류 해결

기본 실행에는 `pnpm`이 필요하지 않는다. 문서대로 `npm.cmd install`, `npm.cmd run dev`를 사용하면 된다. `npm` 대신 반드시 pnpm을 쓰고 싶다면 전역 설치 없이 다음처럼 실행할 수 있다.

```powershell
npx.cmd --yes pnpm@10 install
npx.cmd --yes pnpm@10 dev
```

Node 설치 여부는 다음으로 확인한다.

```powershell
node.exe --version
npm.cmd --version
```

둘 중 하나라도 “인식되지 않는다”가 나오면 Node.js LTS를 설치한 뒤 PowerShell을 완전히 닫았다가 새로 연다.

## 자주 보이는 PowerShell 오류

### `No installed Python found`

Windows에 Python 본체가 없고 `py` 실행기만 남아 있는 상태이다. Python 3.12 x64를 설치하고 새 PowerShell에서 `py -3 --version`이 성공하는지 확인한 뒤 `.venv`를 만든다.

### `Unable to create process using ... Python312`

`.venv`가 현재 존재하지 않는 Python 설치 경로를 참조한다. 위의 `.venv_broken_날짜` 이동 명령으로 보존한 뒤 `py -3 -m venv .venv`를 실행한다.

### `포트 3000/8100이 이미 사용 중`

대부분 같은 서버를 다른 PowerShell에서 이미 실행 중인 경우이다. 기존 서버 창에서 `Ctrl+C`로 종료한 후 다시 실행한다.

프로토타입 계정:

- 상담사: `counselor` / `demo`
- 개별 상담사: 예) `CNS-SEO-00001` / `demo` (저장된 상담사 ID 1,724개 사용 가능)
- 중앙 관리자: `admin` / `demo`

## Docker 실행

Docker 이미지도 Git에 없는 상담 SQLite를 자동 생성하지 않는다. 프로젝트 루트에서 `.env`를 만들고 `backend/data/counseling_demo_v3.sqlite3`을 먼저 생성한 후 실행한다.

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}
if (-not (Test-Path -LiteralPath ".\backend\data\counseling_demo_v3.sqlite3")) {
    & ".\.venv\Scripts\python.exe" ".\backend\scripts\build_counseling_dataset.py" --anchor-date 2026-08-10
}
```

준비가 끝나면:

```powershell
docker compose up --build
```

백엔드의 고정 상담 데이터와 회기 진행 JSON은 `family-center-data` Docker 볼륨에 보존된다. Paddle 모델은 Colab에 올라가므로 로컬 Docker에는 GPU가 필요하지 않고, 교육 MP4도 프론트 정적 파일로 재생된다.

## 내부망 연동

`.env`에서 다음 값을 설정한다.

```text
AI_PROVIDER=internal_openai
INTERNAL_LLM_BASE_URL=http://llm-gateway.internal/v1
INTERNAL_LLM_MODEL=your-model
INTERNAL_LLM_API_KEY=...
OCR_PROVIDER=paddleocr_vl_http
INTERNAL_OCR_URL=http://ocr-gateway.internal/v1/ocr
INTERNAL_OCR_API_KEY=...
INTERNAL_TTS_URL=http://tts.internal/v1/audio/speech
STT_PROVIDER=qwen_http
INTERNAL_STT_URL=http://stt.internal/v1/audio/transcriptions
# 기본값은 static_2d이며 LongCat 전용 GPU 워커가 있을 때만 활성화한다.
AVATAR_PROVIDER=longcat_http
LONGCAT_AVATAR_BASE_URL=http://longcat-avatar.internal
LONGCAT_AVATAR_API_KEY=...
LONGCAT_AVATAR_REQUEST_TIMEOUT=1800
AUTH_SECRET=충분히-긴-무작위-비밀값
```

LLM은 OpenAI 호환 `/chat/completions` 응답을 기대한다. TTS는 `audio_url` JSON을 반환하거나 MP3/WAV 바이너리를 직접 반환할 수 있다. 자세한 내용은 `docs/ARCHITECTURE.md`를 참고한다.

기본 AI 서비스 구성은 `colab/Midm_Base_OpenAI_Server_Colab.ipynb`에서 KT 믿:음 4-bit와 격리된 PaddleOCR-VL 1.6을 함께 실행한다. 영상 생성은 별도의 `colab/LongCat_Avatar15_LowVRAM_Server_Colab.ipynb`에서 실행하며, LongCat은 모델 규모가 커서 믿:음·OCR과 GPU를 공유하지 않는다. 영상 워커는 노트북이 출력한 URL·키를 `.env`에 반영했을 때만 활성화된다. `.env`는 백엔드 시작 시 자동으로 읽으며 값을 바꾼 뒤에는 FastAPI를 다시 시작해야 한다. `AI_PROVIDER=mock`은 화면·계약 확인용 응답이며 실제 생성형 응답이 아니다.

이미지/PDF OCR, 초기상담기록지·상담기록지·SOAP 통합, 회기·종결 보고서를 통합 프론트에 연결했다. OCR 선택 설치와 검수 방식은 `docs/OCR_REPORT_STT.md`를 참고한다.

## 중요: 운영 전 교체할 항목

현재 로그인 토큰과 메모리 저장소는 로컬 데모용이다. 운영 환경에서는 공공기관 SSO/OIDC, PostgreSQL, Redis, 감사로그, 비밀관리 시스템으로 교체해야 한다. 실제 내담자 데이터는 데모에 넣지 않아야 한다. 이 저장소의 페르소나는 실제 인물과 무관한 가상 성인이다.

## 데이터·척도 이용 안내

본 프로젝트는 한국건강가정진흥원 대상 제안 및 기능 검증을 위한 비공식 프로토타입이다. 포함된 상담 사례와 운영 데이터는 실제 개인자료가 아닌 고정 시드 합성데이터다.

### 상담사 발화 훈련 규칙

KMI 외부 합성대화를 이용해 상담사 발화 훈련용 자체 규칙이 의도한 방향으로 동작하는지 점검하였다.

### BFI-10

본 비상업적 교육·연구용 프로토타입에서는 설문 부담을 줄인 성격 5차원 표시 흐름을 검토하기 위해 Rammstedt와 John(2007)의 BFI-10 구조와 GESIS가 제공하는 ISSP 한국어 문항을 기반으로 구현한다.

별도의 국내 연구에서 김선영 등(2010)은 BFI-K-10을 지역사회 노인 1,038명에게 검토하여 장형 BFI-K 및 우울·불안 지표와의 관련성을 확인했다. 이후 BFI-K-10은 65가족의 가족 구성원 195명, 전국 역학조사 참여자 6,022명 중 정신질환 평생진단군 1,544명, 직장인 486명 및 의대생 105명 등의 국내 연구표본에 적용됐다. 이러한 사례는 국내 연구 활용 전례를 보여준다.

- 현재 화면의 차원별 값과 상대적 경향 표시는 고정 시드 합성응답을 이용한 UI·산식 시연이며, 검증된 개인 해석이나 유형 판정이 아니다.
- 해당 값은 실제 개인의 진단, 서비스 대상자 선별 또는 AI 사례분석에 사용하지 않는다.
- 현재 구현은 GESIS/ISSP 한국어 문항판이며, 김선영 등(2010)의 별도 한국판과 출처를 구분한다.
- GESIS는 BFI-10을 시간 제약이 큰 대규모 연구용 도구로 안내하며, 신뢰도상 단일 응답자 추론과 상업적 이용에 사용하지 않도록 명시한다.
- 실제 자료 수집, 개인별 결과 제공 또는 서비스 적용 전에는 원도구와 한국어 적응판 권리자에게 사용 목적·문항 표시·응답방식 변경·배포 범위를 제시하여 서면 이용권리를 확인하고, 대상집단 타당도와 동의·개인정보 처리절차를 별도로 검토한다. 이용권리가 확보되지 않으면 적합한 허가 척도로 교체한다.

원도구: Rammstedt, B., & John, O. P. (2007). *Measuring personality in one minute or less: A 10-item short version of the Big Five Inventory in English and German.* Journal of Research in Personality, 41(1), 203–212. [DOI](https://doi.org/10.1016/j.jrp.2006.02.001)  
한국어 문항·이용 안내: [GESIS BFI-10](https://www.gesis.org/en/services/planning-studies-and-collecting-data/items-scales/bfi-10) · [GESIS/ISSP 한국어 문항](https://www.gesis.org/fileadmin/admin/Dateikatalog/pdf/guidelines/SDMwiki/BFI-10/BFI-10_Korean_Items.pdf)  
국내 근거: [김선영 등(2010)](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001426195) · [가족 구성원 연구](https://doi.org/10.15709/hswr.2016.36.3.34) · [전국 역학조사 기반 연구](https://doi.org/10.1186/s12888-017-1322-2) · [직장인 연구](https://doi.org/10.4306/jknpa.2017.56.4.175) · [의대생 연구](https://doi.org/10.3946/kjme.2016.14)

### 가족관계·가족스트레스 문항

가족관계 및 가족스트레스 문항은 한국건강가정진흥원의 가족센터 관련 척도 자료를 바탕으로 구현한다.

- 현재 구현은 합성사례 기반 제안·시연용이다.
- 점수는 상담사가 원응답과 실제 면담에서 확인할 참고정보이며 진단이나 위험판정을 대체하지 않는다.
- 실제 도입 시 문항, 명칭, 산식 및 자료 이용범위를 한국건강가정진흥원과 확정한다.

### 기관 명칭 및 시각표지

한국건강가정진흥원 및 가족센터의 명칭·로고가 표시된 화면은 제안용 비공식 프로토타입이다. 해당 표시는 기관의 승인, 보증 또는 실제 서비스 운영을 의미하지 않으며, 실제 도입 시 기관의 CI 지침과 승인 범위를 따른다.
