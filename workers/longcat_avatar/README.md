# LongCat-Video-Avatar 1.5 전용 GPU 워커

이 폴더는 전용 GPU가 준비된 환경에서만 선택적으로 실행하는 영상 생성 워커입니다. 가족센터 FastAPI, 믿:음, Qwen TTS, Qwen STT는 이 모듈을 import하지 않으며 기본 개발 설정에서는 모델 다운로드나 GPU 점유가 전혀 발생하지 않습니다.

## 실행 계약

- 모델: `meituan-longcat/LongCat-Video-Avatar-1.5`
- 저메모리 기본값: INT8, 순차 오프로딩, 480p, 동시 작업 1개
- API: `/v1/avatar/status`, `/v1/avatar/render`, `/v1/avatar/media/{filename}`
- 입력: 기존 Qwen TTS의 `audio_url`과 페르소나 PNG
- 출력: 음성이 포함된 MP4
- 장애 시: 가족센터 백엔드가 기본 사진과 기존 TTS로 계속 진행

## 전용 GPU에서만 실행

기존 Colab A100 영상 서버를 대체해 HTTP 워커로 띄울 때는 `colab/LongCat_Avatar15_LowVRAM_Server_Colab.ipynb`를 위에서 아래로 실행합니다. 이 노트북이 공식 코드·모델 가중치·Python 3.10 환경을 `/content/longcat_avatar15`에 준비하고, FastAPI와 ngrok까지 실행합니다.

영상 파일 하나만 직접 제작할 때는 별도의 배치용 `colab/LongCat_Avatar15_LowVRAM_Colab.ipynb`를 사용합니다. LongCat은 경량 립싱크 모델보다 훨씬 무거우므로 믿:음·OCR·TTS와 같은 Colab GPU에 합치지 않고 영상 전용 A100 런타임에서 실행합니다.

```bash
export LONGCAT_WORKER_ROOT=/content/longcat_avatar_worker
export LONGCAT_REPO=/content/longcat_avatar15/repo
export LONGCAT_PYTHON=/content/longcat_avatar15/.venv/bin/python
export LONGCAT_CHECKPOINT=/content/longcat_avatar15/weights/LongCat-Video-Avatar-1.5
export LONGCAT_LOWMEM_SCRIPT=/content/longcat_avatar15/repo/run_demo_avatar_single_lowmem.py
export LONGCAT_RESOLUTION=480p
export LONGCAT_WORKER_API_KEY='replace-with-a-secret'

/content/longcat_avatar15/.venv/bin/python -m pip install -r workers/longcat_avatar/requirements.txt
/content/longcat_avatar15/.venv/bin/python -m uvicorn workers.longcat_avatar.app:app --host 0.0.0.0 --port 8015
```

충분한 전용 GPU에서는 `LONGCAT_RESOLUTION=720p`로 올릴 수 있습니다. LLM/TTS/STT와 같은 GPU에서 동시에 실행하는 구성은 메모리와 지연 안정성 때문에 권장하지 않습니다.

## 가족센터에서 명시적으로 활성화

기본 `.env`에서는 다음 설정을 사용하므로 워커에 연결되지 않습니다.

```text
AVATAR_PROVIDER=static_2d
```

전용 워커가 검증된 환경에서만 아래처럼 변경합니다.

```text
AVATAR_PROVIDER=longcat_http
LONGCAT_AVATAR_BASE_URL=https://longcat-avatar.example
LONGCAT_AVATAR_API_KEY=replace-with-the-same-secret
LONGCAT_AVATAR_REQUEST_TIMEOUT=1800
```

첫 시연 응답은 생성 지연을 피하기 위해 사전 제작 MP4를 계속 우선 사용합니다.
