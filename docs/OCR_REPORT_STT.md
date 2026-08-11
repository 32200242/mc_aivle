# Colab OCR·통합 기록·보고서 사용법

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

OCR 이외의 기록·보고서 기능은 기본 설치만으로 동작합니다. 이미지/PDF OCR을 사용하려면 로컬 백엔드에 전처리 패키지를 설치하고, 수정된 Colab 노트북의 PaddleOCR 사이드카 셀까지 실행합니다.

로컬 백엔드는 PDF를 이미지로 변환하고 원본·강화본을 최대 4장씩 묶어 Colab으로 보냅니다. Paddle 모델과 Transformers 5는 로컬 PC가 아니라 Colab의 격리 프로세스에서 실행됩니다.

### 1. 백엔드 종료

백엔드 로그가 보이는 PowerShell 1을 클릭하고 `Ctrl+C`를 누릅니다.

### 2. 프로젝트 루트에서 OCR 패키지 설치

```powershell
Set-Location -LiteralPath "C:\Users\User\Documents\Codex\2026-07-31\1-2-3-4-5-6\outputs\family_center_platform_v0_4"
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements-ocr.txt"
```

이 명령은 OpenCV, Pillow, PyMuPDF만 로컬에 설치합니다. PyTorch와 Transformers 5는 설치하지 않습니다.

### 3. 백엔드 재실행

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

프론트엔드는 재시작하지 않아도 됩니다. 브라우저의 코파일럿 화면을 새로고침하고 OCR 상태가 `사용 가능`으로 바뀌었는지 확인합니다.

Colab에서 `Midm_Base_OpenAI_Server_Colab.ipynb`을 끝까지 실행합니다. 마지막 OCR 셀이 별도 Transformers 5 가상환경과 `/v1/ocr` 프록시를 만들고 `.env` 값을 출력합니다. 첫 OCR 요청에서 `PaddlePaddle/PaddleOCR-VL-1.6` 모델을 한 번 내려받아 GPU에 올리므로 첫 요청만 오래 걸릴 수 있습니다.

### 설치 확인

백엔드를 실행하기 전에 다음 명령으로 필수 모듈을 확인할 수 있습니다.

```powershell
& ".\.venv\Scripts\python.exe" -c "import cv2, fitz, PIL; print('OCR 전처리 패키지 설치 정상')"
```

`Unable to create process using ... Python312`가 나오면 OCR 문제가 아니라 `.venv`가 깨진 상태입니다. 프로젝트 루트 [`README.md`](../README.md)의 `Unable to create process` 해결 절차로 가상환경을 다시 만든 뒤, 기본 패키지와 OCR 패키지를 차례대로 설치합니다.

지원 형식과 제한:

- PNG, JPG, JPEG, WEBP, TIF, TIFF, PDF
- 한 번에 최대 5개
- 파일당 기본 12MB
- PDF 기본 12페이지
- 원본, 대비 강화, 문서 강화, 원본+대비 강화

설정값:

```text
OCR_PROVIDER=paddleocr_vl_http
INTERNAL_OCR_URL=https://발급주소.ngrok-free.dev/v1/ocr
INTERNAL_OCR_API_KEY=Colab이_출력한_키
OCR_REQUEST_TIMEOUT=300
OCR_HEALTH_TIMEOUT=12
OCR_REMOTE_BATCH_SIZE=4
PADDLE_OCR_MODEL_ID=PaddlePaddle/PaddleOCR-VL-1.6
PADDLE_OCR_MAX_NEW_TOKENS=512
OCR_MAX_FILE_MB=12
OCR_MAX_PDF_PAGES=12
```

### 채택 근거와 강제 검수 규칙

내부 192개 표본 비교에서 PaddleOCR-VL 1.6은 내용 CER 0.78%, 내용 완전일치 163/192(84.9%), 중요 문구 정확도 96.43%를 기록해 Qwen OCR보다 우세했습니다. 다만 중요 문구 84개 중 3개를 놓쳤고, 목표로 정한 99%에 미달했으므로 자동 확정 모델로 사용하지 않습니다.

- 모델은 Colab 사이드카 프로세스에서 한 번 로딩한 뒤 재사용합니다.
- SOAP S 필드, 위험·안전 문구, 매우 짧은 출력은 원본·강화본 재인식 대상으로 처리합니다.
- 두 인식문의 길이 비율이 0.78 미만이거나, 충분히 긴 문장의 유사도가 0.82 미만이면 부분 누락 의심으로 표시합니다.
- `업엽고`, `자사사` 등 벤치마크에서 확인된 위험 문구 오인식 형태도 별도 경고합니다.
- OCR 결과가 있으면 상담사가 원본을 보고 수정한 뒤 `원본 검수 완료`를 선택해야 합니다.
- API를 직접 호출해도 `ocr_reviewed=false`이면 기록 생성이 HTTP 409로 거부됩니다.

이 규칙은 누락을 완벽하게 검출한다는 뜻이 아닙니다. 특히 이미지에서 문장 전체가 사라지면 위험 단어 검색만으로는 발견할 수 없으므로, 화면의 원본 미리보기와 재인식 차이를 사람이 최종 확인해야 합니다.

## KT Cloud 전환

프론트와 기록 API는 Colab 주소를 직접 알지 못하며 로컬 FastAPI의 OCR 어댑터만 호출합니다. 따라서 KT Cloud로 옮길 때는 동일 계약의 GPU 서비스를 만들고 환경변수만 바꿉니다.

```text
GET  /v1/ocr/status
POST /v1/ocr
Authorization: Bearer <key>
요청: {"images":["PNG_BASE64", "..."]}
응답: {"model":"PaddlePaddle/PaddleOCR-VL-1.6", "texts":["전사문", "..."]}
```

```text
OCR_PROVIDER=paddleocr_vl_http
INTERNAL_OCR_URL=http://paddleocr-vl.internal/v1/ocr
INTERNAL_OCR_API_KEY=KT_내부_API_키
```

Mi:dm의 Transformers 4와 Paddle의 Transformers 5가 충돌하지 않도록 KT에서도 별도 컨테이너 또는 가상환경으로 운영합니다. 같은 GPU를 공유하면 단일 작업 큐로 순차 실행하고, 동시 사용량이 늘면 LLM과 OCR GPU를 분리합니다. 이 조건을 지키면 프론트·검수 UI·기록 저장 코드는 변경하지 않습니다.

OCR 패키지가 없어도 코파일럿의 `OCR 정제 텍스트`에 기존 OCR 결과나 수기 내용을 직접 붙여 넣어 통합 기록과 보고서를 시험할 수 있습니다.

## 교육 화면

교육 탭은 기존 가상 내담자 대화·비언어 행동·슈퍼바이저 피드백·STT 화면을 사용합니다. 첫 기본 질문의 응답은 고정하고 `frontend/public/training/lee-jieun-counselor-training-final.mp4`를 즉시 재생합니다. 이후 질문은 믿:음 응답 스트림과 기존 TTS를 사용하며, 별도 LongCat GPU 워커가 명시적으로 활성화된 환경에서만 영상을 생성합니다. 워커가 없거나 실패하면 기본 사진과 브라우저 음성으로 전환합니다.

## 운영 전환 전 확인

- 실제 상담 DB와 업로드 파일은 내부망 저장소 사용
- 파일 악성코드 검사와 보존기간 정책 추가
- OCR 원본·정제문·상담사 수정본의 변경 이력 저장
- 보고서 생성·수정·확정자 감사로그
- AI 초안과 상담사 확정본을 데이터 모델에서 명확히 분리
