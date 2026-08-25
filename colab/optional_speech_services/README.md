# 선택적 Qwen3 TTS·ASR 서비스

`Midm_Qwen3_TTS_ASR_MuseTalk_A100_Colab.ipynb`은 백엔드 음성 어댑터와 호환되는 선택적
Qwen3 TTS·ASR FastAPI 서비스를 제공한다. 기본 화면 구성에는 필요하지 않으며, 서버 기반
음성 합성·인식을 사용할 때만 별도 GPU 런타임에서 실행한다.

## 백엔드 연결 설정

노트북을 실행한 뒤 출력된 `PUBLIC_URL`과 API 키를 사용해 루트 `.env`에 다음 값만 반영한다.

```dotenv
INTERNAL_TTS_URL=https://발급된주소/v1/audio/speech
INTERNAL_TTS_API_KEY=노트북이_출력한_API_KEY
TTS_REQUEST_TIMEOUT=180

STT_PROVIDER=qwen_http
INTERNAL_STT_URL=https://발급된주소/v1/audio/transcriptions
INTERNAL_STT_API_KEY=노트북이_출력한_API_KEY
STT_REQUEST_TIMEOUT=120
STT_HEALTH_TIMEOUT=8
```

현재 `backend/app/services/tts.py`는 JSON 요청 후 WAV 응답을 받고,
`backend/app/services/stt.py`는 multipart 파일을 보내 `text` 응답을 받는다. 노트북의
`/v1/audio/speech`, `/v1/audio/transcriptions`, `/v1/speech/status` 경로가 이 계약에 대응한다.
호환성 평가는 HTTP 경로와 요청·응답 계약의 정적 점검을 기준으로 한다. 운영 전에는 대상 GPU
환경에서 음질, 인식률, 지연시간, 오류복구를 포함한 종단간 수용시험이 필요하다.

## 지원하지 않는 아바타 환경변수

노트북 마지막 셀에 표시되는 다음 키는 현재 백엔드 아바타 어댑터가 사용하지 않는다.

- `AVATAR_PROVIDER=internal_http`
- `INTERNAL_AVATAR_BASE_URL`
- `INTERNAL_AVATAR_API_KEY`
- `AVATAR_REQUEST_TIMEOUT`

현재 아바타는 `../LongCat_Avatar15_LowVRAM_Server_Colab.ipynb`을 사용하고 아래처럼 연결한다.

```dotenv
AVATAR_PROVIDER=longcat_http
LONGCAT_AVATAR_BASE_URL=https://LongCat_서버주소
LONGCAT_AVATAR_API_KEY=LongCat_노트북이_출력한_API_KEY
LONGCAT_AVATAR_REQUEST_TIMEOUT=1800
```

LLM과 OCR의 기준 노트북도 현재 버전의 `../Midm_Base_OpenAI_Server_Colab.ipynb`이다. 이 통합
노트북의 `.env` 예시에서는 TTS/STT 항목만 적용한다. 실제 개인정보나 상담 원문을 공개
터널로 전송해서는 안 되며, 기관 데이터 연동에는 인증된 전용 네트워크와 접근통제가 필요하다.
