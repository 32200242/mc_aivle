from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BATCH_NOTEBOOK = PROJECT_ROOT / "colab" / "LongCat_Avatar15_LowVRAM_Colab.ipynb"
OUTPUT_NOTEBOOK = PROJECT_ROOT / "colab" / "LongCat_Avatar15_LowVRAM_Server_Colab.ipynb"
WORKER_SOURCE = PROJECT_ROOT / "workers" / "longcat_avatar" / "app.py"
WORKER_REQUIREMENTS = PROJECT_ROOT / "workers" / "longcat_avatar" / "requirements.txt"


def markdown(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def main() -> None:
    batch = json.loads(BATCH_NOTEBOOK.read_text(encoding="utf-8"))
    install_cell = next(cell for cell in batch["cells"] if cell.get("id") == "install-download")
    worker_source = WORKER_SOURCE.read_text(encoding="utf-8")
    worker_requirements = WORKER_REQUIREMENTS.read_text(encoding="utf-8")

    cells = [
        markdown(
            """# LongCat-Video-Avatar 1.5 저메모리 HTTP 서버 · Colab A100

이 노트북은 가족센터 앱과 자동 연결되지 않습니다. 전용 GPU가 있는 환경에서만 실행하고, 마지막 셀이 출력하는 값을 로컬 `.env`에 **수동으로 반영한 경우에만** 앱이 LongCat 워커를 호출합니다.

기존 A100 영상 사이드카가 담당하던 HTTP 아바타 서버 자리를 LongCat으로 교체하기 위한 노트북입니다. LongCat은 경량 립싱크 모델보다 훨씬 무거우므로 믿:음·OCR·TTS와 같은 GPU에서 함께 실행하지 않고, 별도의 Colab A100 런타임을 영상 생성 전용으로 사용합니다.

- API: `/v1/avatar/status`, `/v1/avatar/render`, `/v1/avatar/media/{filename}`
- 기본 생성: INT8, 순차 오프로딩, 480p, 동시 작업 1개
- 권장 GPU: A100 40GB 이상과 시스템 RAM 45GiB 이상
- Colab Secrets: `NGROK_AUTHTOKEN` 필수, `LONGCAT_WORKER_API_KEY` 선택
- Colab 탭과 런타임이 살아 있는 동안만 동작하며 재연결하면 URL이 바뀝니다.
- 실제 내담자 사진·음성은 사용하지 말고 합성 교육 페르소나만 사용하세요.
"""
        ),
        markdown("## 1. Drive, GPU, RAM 및 저장공간 확인\n"),
        code(
            """import os, re, shutil, subprocess, sys, time, secrets
from pathlib import Path
from google.colab import drive, userdata

drive.mount('/content/drive')

gpu_line = subprocess.check_output([
    'nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'
]).decode().strip()
print('GPU:', gpu_line)
gpu_memory_mib = int(gpu_line.rsplit(',', 1)[1].strip())
if gpu_memory_mib < 38000:
    raise RuntimeError('최소 A100 40GB급 GPU가 필요합니다.')

with open('/proc/meminfo', encoding='utf-8') as meminfo:
    mem_total_kib = int(re.search(r'MemTotal:\\s+(\\d+)', meminfo.read()).group(1))
ram_gib = mem_total_kib / 1024**2
print(f'시스템 RAM: {ram_gib:.1f} GiB')
if ram_gib < 45:
    raise RuntimeError('저메모리 워커도 시스템 RAM 45GiB 이상이 필요합니다.')

free_gib = shutil.disk_usage('/content').free / 1024**3
print(f'/content 빈 공간: {free_gib:.1f} GiB')
if free_gib < 120:
    raise RuntimeError('/content에 최소 120GiB의 빈 공간이 필요합니다.')

ROOT = Path('/content/longcat_avatar15')
OUTPUT_DIR = ROOT / 'outputs'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print('전용 런타임 검사 완료')
"""
        ),
        markdown("## 2. 공식 코드·전용 Python 3.10 환경·필요 가중치 준비\n최초 실행에는 모델 다운로드 시간이 필요합니다. 모델은 `/content`에만 저장됩니다.\n"),
        {**install_cell, "execution_count": None, "outputs": []},
        markdown("## 3. 저메모리 연속 생성 패치 확인\n"),
        code(
            """LOWMEM_SCRIPT = REPO / 'run_demo_avatar_single_lowmem.py'
lowmem_text = LOWMEM_SCRIPT.read_text(encoding='utf-8')
lowmem_text = lowmem_text.replace(
    'generator.manual_seed(42 + global_rank)',
    "generator.manual_seed(int(os.environ.get('LONGCAT_SEED', '42')) + global_rank)"
)
lowmem_text = lowmem_text.replace('offload_kv_cache=False', 'offload_kv_cache=True')
LOWMEM_SCRIPT.write_text(lowmem_text, encoding='utf-8')
print('시드 제어와 KV 캐시 CPU 오프로딩 적용 완료')
"""
        ),
        markdown("## 4. 가족센터 LongCat 워커 코드 배치\n워커 코드는 이 노트북 생성 시 저장소의 `workers/longcat_avatar/app.py`에서 자동 포함됩니다.\n"),
        code(
            """WORKER_PROJECT = Path('/content/family_center_longcat_worker')
PACKAGE_DIR = WORKER_PROJECT / 'workers' / 'longcat_avatar'
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
(WORKER_PROJECT / 'workers' / '__init__.py').write_text('', encoding='utf-8')
(PACKAGE_DIR / '__init__.py').write_text('', encoding='utf-8')
WORKER_SOURCE = """
            + repr(worker_source)
            + """
WORKER_REQUIREMENTS = """
            + repr(worker_requirements)
            + """
(PACKAGE_DIR / 'app.py').write_text(WORKER_SOURCE, encoding='utf-8')
(PACKAGE_DIR / 'requirements.txt').write_text(WORKER_REQUIREMENTS, encoding='utf-8')

subprocess.run([
    'uv', 'pip', 'install', '--python', str(PYTHON),
    '-r', str(PACKAGE_DIR / 'requirements.txt')
], check=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'pyngrok>=7,<8', 'requests>=2.32,<3'], check=True)
print('워커 코드와 서버 패키지 준비 완료:', WORKER_PROJECT)
"""
        ),
        markdown("## 5. Uvicorn 시작 및 로컬 상태 검증\n이 셀은 워커만 시작하며 가족센터 앱 설정은 변경하지 않습니다.\n"),
        code(
            """import requests

SERVER_PORT = 8015
try:
    WORKER_API_KEY = userdata.get('LONGCAT_WORKER_API_KEY')
except Exception:
    WORKER_API_KEY = None
WORKER_API_KEY = WORKER_API_KEY or secrets.token_urlsafe(32)

server_env = os.environ.copy()
server_env.update({
    'PYTHONPATH': str(WORKER_PROJECT),
    'LONGCAT_WORKER_ROOT': '/content/longcat_avatar_worker',
    'LONGCAT_REPO': str(REPO),
    'LONGCAT_PYTHON': str(PYTHON),
    'LONGCAT_CHECKPOINT': str(AVATAR_MODEL),
    'LONGCAT_LOWMEM_SCRIPT': str(LOWMEM_SCRIPT),
    'LONGCAT_RESOLUTION': '480p',
    'LONGCAT_WORKER_API_KEY': WORKER_API_KEY,
    'LONGCAT_SEED': '29411',
})

if 'longcat_server_process' in globals() and longcat_server_process.poll() is None:
    longcat_server_process.terminate()
    longcat_server_process.wait(timeout=15)
if 'longcat_server_log_handle' in globals() and not longcat_server_log_handle.closed:
    longcat_server_log_handle.close()

server_log_path = Path('/content/longcat_avatar_worker/server.log')
server_log_path.parent.mkdir(parents=True, exist_ok=True)
longcat_server_log_handle = server_log_path.open('a', encoding='utf-8')
longcat_server_process = subprocess.Popen([
    str(PYTHON), '-m', 'uvicorn', 'workers.longcat_avatar.app:app',
    '--host', '127.0.0.1', '--port', str(SERVER_PORT), '--log-level', 'info'
], cwd=str(WORKER_PROJECT), env=server_env, stdout=longcat_server_log_handle, stderr=subprocess.STDOUT)

headers = {'Authorization': f'Bearer {WORKER_API_KEY}'}
deadline = time.time() + 45
local_status = None
while time.time() < deadline:
    if longcat_server_process.poll() is not None:
        break
    try:
        response = requests.get(f'http://127.0.0.1:{SERVER_PORT}/v1/avatar/status', headers=headers, timeout=3)
        if response.ok:
            local_status = response.json()
            break
    except requests.RequestException:
        pass
    time.sleep(1)
if not local_status:
    tail = server_log_path.read_text(encoding='utf-8', errors='replace').splitlines()[-50:]
    raise RuntimeError('LongCat 로컬 서버 시작 실패:\\n' + '\\n'.join(tail))
if local_status.get('status') != 'ok':
    raise RuntimeError(f'LongCat 워커 준비 미완료: {local_status}')
print('로컬 LongCat API 정상:', local_status)
"""
        ),
        markdown("## 6. ngrok HTTPS 공개 및 외부 상태 검증\nColab Secrets의 `NGROK_AUTHTOKEN`이 필요합니다. 출력값을 복사하기 전까지 로컬 앱에는 연결되지 않습니다.\n"),
        code(
            """from pyngrok import ngrok

try:
    NGROK_AUTHTOKEN = userdata.get('NGROK_AUTHTOKEN')
except Exception:
    NGROK_AUTHTOKEN = None
if not NGROK_AUTHTOKEN:
    raise RuntimeError('Colab Secrets에 NGROK_AUTHTOKEN을 추가하고 노트북 액세스를 허용하세요.')

ngrok.set_auth_token(NGROK_AUTHTOKEN)
try:
    if 'longcat_tunnel' in globals():
        ngrok.disconnect(longcat_tunnel.public_url)
except Exception:
    pass
longcat_tunnel = ngrok.connect(SERVER_PORT, 'http')
PUBLIC_URL = longcat_tunnel.public_url.replace('http://', 'https://').rstrip('/')

public_headers = {
    'Authorization': f'Bearer {WORKER_API_KEY}',
    'ngrok-skip-browser-warning': '1',
}
external = requests.get(f'{PUBLIC_URL}/v1/avatar/status', headers=public_headers, timeout=30)
external.raise_for_status()
external_body = external.json()
if external_body.get('status') != 'ok':
    raise RuntimeError(f'외부 LongCat 상태가 정상이 아닙니다: {external_body}')

print('\\n===== 전용 GPU 워커를 실제 연결할 때만 .env에 넣을 값 =====')
print('AVATAR_PROVIDER=longcat_http')
print(f'LONGCAT_AVATAR_BASE_URL={PUBLIC_URL}')
print(f'LONGCAT_AVATAR_API_KEY={WORKER_API_KEY}')
print('LONGCAT_AVATAR_REQUEST_TIMEOUT=7200')
print('\\n외부 상태 검증 완료:', external_body)
print('이 값을 반영하지 않으면 가족센터는 계속 static_2d이며 GPU 워커를 호출하지 않습니다.')
"""
        ),
        markdown(
            """## 7. 연결·종료 기준

1. 실제 연결 시험 때만 6번 셀의 네 줄을 로컬 `.env`에 반영합니다.
2. FastAPI를 재시작한 뒤 `/api/v1/avatar/status`에서 `provider=longcat_http`, `reachable=true`를 확인합니다.
3. LongCat은 가벼운 실시간 립싱크 모델이 아닙니다. 첫 시연 응답은 사전 제작 MP4를 계속 사용하고, 이 서버는 고품질 후속 영상을 비동기 또는 사전 생성할 때 사용합니다.
4. 연결 시험이 끝나면 로컬 `.env`를 `AVATAR_PROVIDER=static_2d`로 되돌립니다.
5. Colab 런타임을 종료하면 Uvicorn·ngrok·GPU 모델이 모두 내려갑니다.
"""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"name": OUTPUT_NOTEBOOK.name, "provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT_NOTEBOOK.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_NOTEBOOK)


if __name__ == "__main__":
    main()
