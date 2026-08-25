from __future__ import annotations

import ast
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    PROJECT_ROOT / "colab" / "LongCat_Avatar15_LowVRAM_Colab.ipynb",
    PROJECT_ROOT / "deliverables" / "LongCat_Avatar15_A10040_80GB_Colab_v3.ipynb",
)
def source_lines(value: str) -> list[str]:
    return value.splitlines(keepends=True)


INTRO = """# Qwen3-TTS + LongCat-Video-Avatar 1.5 — 감정 음성·영상 완전 자동 생성

이 노트북은 완전히 새로운 Google Colab A100 런타임을 기준으로 합니다.

- 이미지: Base64로 내장하지 않고 Google Drive의 기존 페르소나 PNG를 직접 사용합니다.
- 음성: Qwen3-TTS 1.7B CustomVoice의 한국어 여성 화자 `Sohee`를 고정하고, 한 번의 생성 안에서 감정 흐름을 바꿉니다.
- 영상: LongCat-Video-Avatar 1.5가 작은 입·턱 움직임, 자연스러운 표정과 눈 깜빡임을 생성합니다.
- A100 40GB: 저메모리 순차 로딩과 720p→480p OOM 자동 대체를 사용합니다.
- A100 80GB: 일반 단일 GPU 모드를 자동 적용합니다.
- Qwen TTS는 별도 프로세스에서 먼저 실행한 뒤 종료하므로 LongCat과 GPU 메모리를 동시에 점유하지 않습니다.
- 모델과 중간 파일은 `/content`, 이미지·자동 생성 WAV·최종 MP4만 Google Drive에 저장합니다.
- Drive에 페르소나 PNG가 준비되어 있으면 미리보기 선택이나 시드 입력 없이 **런타임 → 모두 실행**만 누르면 최종 MP4까지 생성됩니다.
"""


MOUNT_IMAGE = """# 1. 드라이브 마운트, A100/공간 확인, 이미지 준비
import os, re, math, json, shutil, subprocess, sys
from pathlib import Path
from google.colab import drive, files

drive.mount('/content/drive')

gpu_line = subprocess.check_output([
    'nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'
]).decode().strip()
print('GPU:', gpu_line)
gpu_memory_mib = int(gpu_line.rsplit(',', 1)[1].strip())
if gpu_memory_mib < 38000:
    raise RuntimeError('최소 A100 40GB급 GPU가 필요합니다. 런타임 GPU를 다시 선택하세요.')
LOW_VRAM = gpu_memory_mib < 70000
print('실행 모드:', 'A100 40GB CPU 오프로딩' if LOW_VRAM else 'A100 80GB 일반 모드')

with open('/proc/meminfo', encoding='utf-8') as meminfo:
    mem_total_kib = int(re.search(r'MemTotal:\\s+(\\d+)', meminfo.read()).group(1))
ram_gib = mem_total_kib / 1024**2
print(f'시스템 RAM: {ram_gib:.1f} GiB')
if LOW_VRAM and ram_gib < 45:
    raise RuntimeError('A100 40GB 모드는 CPU 오프로딩을 위해 시스템 RAM 45GiB 이상이 필요합니다.')

free_gib = shutil.disk_usage('/content').free / 1024**3
print(f'/content 빈 공간: {free_gib:.1f} GiB')
if free_gib < 120:
    raise RuntimeError('/content에 최소 120GiB의 빈 공간이 필요합니다.')

ROOT = Path('/content/longcat_avatar15')
INPUT_DIR = ROOT / 'inputs'
OUTPUT_DIR = ROOT / 'outputs'
DRIVE_DIR = Path('/content/drive/MyDrive/longcat_avatar15')
for folder in (INPUT_DIR, OUTPUT_DIR, DRIVE_DIR / 'inputs', DRIVE_DIR / 'outputs'):
    folder.mkdir(parents=True, exist_ok=True)

SOURCE_IMAGE = INPUT_DIR / 'lee_jieun_source_neutral.png'
SOURCE_AUDIO = INPUT_DIR / 'lee_jieun_speech_v10_sohee_one_second_pause.wav'
PADDED_AUDIO = INPUT_DIR / 'lee_jieun_speech_v10_sohee_one_second_pause_padded.wav'
DRIVE_IMAGE = DRIVE_DIR / 'inputs' / SOURCE_IMAGE.name
DRIVE_AUDIO = DRIVE_DIR / 'inputs' / SOURCE_AUDIO.name

if not DRIVE_IMAGE.exists():
    legacy_images = [
        Path('/content/drive/MyDrive/portrait_video_studio/inputs/images/lee_jieun_hurt.png'),
        Path('/content/drive/MyDrive/portrait_video_studio/inputs/images/lee_jieun_source_neutral.png'),
    ]
    legacy_image = next((path for path in legacy_images if path.exists()), None)
    if legacy_image:
        shutil.copy2(legacy_image, DRIVE_IMAGE)
        print('기존 portrait_video_studio 이미지를 자동으로 가져왔습니다:', legacy_image)
    else:
        raise FileNotFoundError(
            'Base64 내장 이미지를 제거했습니다. lee_jieun_source_neutral.png 파일을 먼저 다음 위치에 넣어주세요: '
            + str(DRIVE_IMAGE)
        )
print('Google Drive의 페르소나 이미지를 사용합니다:', DRIVE_IMAGE)

shutil.copy2(DRIVE_IMAGE, SOURCE_IMAGE)
print('이미지 준비 완료:', SOURCE_IMAGE)
"""


AUTO_TTS = r'''# 2. Qwen3-TTS 최신 CustomVoice · 한국어 여성 Sohee · 자연스러운 두 구간 생성
BASE_INSTRUCT = (
    '한국어 여성 화자 Sohee의 원래 목소리로, 가족상담실에서 바로 앞 사람에게 실제 경험을 '
    '이야기한다. 같은 음색과 같은 나이의 한 사람이 계속 말한다. 문장을 읽어 주거나 연기하지 말고, '
    '평범한 대화처럼 자연스럽게 말한다. 일상 대화보다 아주 조금 빠르되 서두르지는 않는다.'
)
TTS_SEGMENTS = [
    {
        'text': (
            '제가 남편이랑 얘기를 좀 해보려고 하면요, 남편은 제 말을 자기를 탓하는 걸로 받아들여요. '
            '사실 저는 싸우자는 게 아니고, 그냥 우리 사이가 좀 나아졌으면 해서 말을 꺼낸 건데.'
        ),
        'instruct': BASE_INSTRUCT + (
            ' 아직 감정을 크게 드러내지 않고 차분하게 설명한다. 말에 힘을 주거나 또박또박 '
            '낭독하지 않으며, 자연스러운 한국어 구어체 리듬으로 말한다.'
        ),
    },
    {
        'text': (
            '하.. 그런데 얘기가 끝나고 나면, 제 마음은 하나도 전해지지 않은 것 같아요. '
            '그게 너무 서운하고… 이제는 저도 좀 지쳐요'
        ),
        'instruct': BASE_INSTRUCT + (
            ' 앞부분과 같은 목소리와 거의 같은 속도를 유지한다. 하.. 뒤에는 애써 차분함을 '
            '유지하지만 실망과 허탈함이 분명히 드러난다. 서운하고에서 목이 잠깐 메이고, '
            '지쳐요에서는 숨이 살짝 섞이며 말끝의 힘이 빠진다. 울거나 흐느끼지는 않는다.'
        ),
    },
]

def tts_run(command, *, env=None):
    print('\n$', ' '.join(map(str, command)))
    subprocess.run(list(map(str, command)), env=env, check=True)

if not DRIVE_AUDIO.exists() or DRIVE_AUDIO.stat().st_size < 100_000:
    TTS_ROOT = Path('/content/qwen3_tts_sohee_one_second_pause_v10')
    # Colab에는 CUDA PyTorch가 이미 설치되어 있다. 빈 uv 환경에 수 GB의 PyTorch를
    # 다시 설치하지 않고 공식 Qwen3-TTS 권장 Python 3.12 런타임을 그대로 사용한다.
    TTS_PYTHON = Path(sys.executable)
    TTS_HF_CACHE = TTS_ROOT / 'hf_cache'
    TTS_ROOT.mkdir(parents=True, exist_ok=True)

    tts_run(['apt-get', '-qq', 'update'])
    tts_run(['apt-get', '-qq', 'install', '-y', 'ffmpeg', 'sox', 'libsox-fmt-all', 'libsndfile1'])
    tts_run([str(TTS_PYTHON), '-c',
             "import torch; assert torch.cuda.is_available(); "
             "print('Colab torch:', torch.__version__, '/', torch.cuda.get_device_name(0))"])
    tts_run([str(TTS_PYTHON), '-m', 'pip', 'install', '-q',
             '--upgrade-strategy', 'only-if-needed', 'qwen-tts', 'soundfile'])

    tts_job = TTS_ROOT / 'job.json'
    raw_audio = TTS_ROOT / 'speech_raw.wav'
    tts_job.write_text(json.dumps({
        'segments': TTS_SEGMENTS,
        'output': str(raw_audio),
        'seed': 17321,
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    tts_script = TTS_ROOT / 'generate.py'
    tts_script.write_text("""
import json, random, sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
seed = int(job['seed'])
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
    device_map='cuda:0',
    dtype=torch.bfloat16,
)
wavs, sample_rate = model.generate_custom_voice(
    text=[item['text'] for item in job['segments']],
    language=['Korean'] * len(job['segments']),
    speaker=['Sohee'] * len(job['segments']),
    instruct=[item['instruct'] for item in job['segments']],
    max_new_tokens=2048,
)
# 전체 WAV를 뒤에서 1.035배 빠르게 처리하므로, 여기서는 1.035초를 넣어
# 최종 음성에서 '결국' 직전의 실제 무음이 정확히 약 1.00초가 되게 한다.
PRE_ATEMPO_GAP_SECONDS = 1.035
parts = []
for index, wav in enumerate(wavs):
    audio = np.asarray(wav, dtype=np.float32).reshape(-1)
    fade_samples = min(int(sample_rate * 0.008), max(1, len(audio) // 4))
    fade = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    audio[:fade_samples] *= fade
    audio[-fade_samples:] *= fade[::-1]
    parts.append(audio)
    if index == 0:
        parts.append(np.zeros(int(sample_rate * PRE_ATEMPO_GAP_SECONDS), dtype=np.float32))
combined = np.concatenate(parts)
sf.write(job['output'], combined, sample_rate, subtype='PCM_16')
print(job['output'], sample_rate, len(combined) / sample_rate,
      'speaker=Sohee two-part / final gap before 결국=1.00s')
""".strip() + '\n', encoding='utf-8')

    tts_environment = os.environ.copy()
    tts_environment['HF_HOME'] = str(TTS_HF_CACHE)
    tts_environment['PYTHONUNBUFFERED'] = '1'
    tts_run([str(TTS_PYTHON), str(tts_script), str(tts_job)], env=tts_environment)
    if not raw_audio.exists() or raw_audio.stat().st_size < 100_000:
        raise RuntimeError('Qwen3-TTS가 유효한 WAV를 생성하지 못했습니다.')
    # 음색과 피치를 유지하는 FFmpeg atempo로 전체 속도만 3.5% 높인다.
    tts_run([
        'ffmpeg', '-y', '-v', 'warning', '-i', str(raw_audio),
        '-filter:a', 'atempo=1.035', '-c:a', 'pcm_s16le', str(SOURCE_AUDIO)
    ])
    shutil.copy2(SOURCE_AUDIO, DRIVE_AUDIO)

    # 음성 생성 프로세스는 이미 종료되었다. LongCat 설치 공간을 위해 모델 캐시만 제거한다.
    shutil.rmtree(TTS_HF_CACHE, ignore_errors=True)
    print('Qwen TTS 임시 환경 정리 완료')
else:
    print('이미 자동 생성된 감정 음성을 Google Drive에서 재사용합니다.')

shutil.copy2(DRIVE_AUDIO, SOURCE_AUDIO)
subprocess.run([
    'ffmpeg', '-y', '-v', 'warning', '-i', str(SOURCE_AUDIO),
    '-af', 'adelay=700:all=1,apad=pad_dur=1.2',
    '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(PADDED_AUDIO)
], check=True)

duration = float(subprocess.check_output([
    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1', str(SOURCE_AUDIO)
]).decode().strip())
print(f'감정 음성 자동 생성 완료: {SOURCE_AUDIO} ({duration:.2f}초)')
'''


AUTO_CONFIG = """# 5. 고정 시드와 렌더 명령 자동 설정 — 검수 입력 없음
from IPython.display import Video, display

BEST_SEED = 29411
RESOLUTION = '720p'

def avatar_command(output_dir, seed, num_segments, *, ref_img_index=None, mask_frame_range=None):
    if LOW_VRAM:
        command = [
            str(PYTHON), '-m', 'torch.distributed.run', '--nproc_per_node=1',
            str(LOWMEM_SCRIPT),
            '--checkpoint_dir', str(AVATAR_MODEL),
            '--stage_1', 'ai2v',
            '--input_json', str(JOB_JSON),
            '--resolution', RESOLUTION,
            '--num_segments', str(num_segments),
            '--output_dir', str(output_dir),
        ]
    else:
        command = [
            str(PYTHON), '-m', 'torch.distributed.run', '--nproc_per_node=1',
            str(REPO / 'run_demo_avatar_single_audio_to_video.py'),
            '--context_parallel_size=1',
            '--checkpoint_dir', str(AVATAR_MODEL),
            '--stage_1', 'ai2v',
            '--input_json', str(JOB_JSON),
            '--model_type', 'avatar-v1.5',
            '--use_distill', '--use_int8',
            '--resolution', RESOLUTION,
            '--num_segments', str(num_segments),
            '--output_dir', str(output_dir),
        ]
    if ref_img_index is not None:
        command += ['--ref_img_index', str(ref_img_index)]
    if mask_frame_range is not None:
        command += ['--mask_frame_range', str(mask_frame_range)]
    environment = os.environ.copy()
    environment['LONGCAT_SEED'] = str(seed)
    environment['LONGCAT_AUDIO_GUIDANCE_SCALE'] = '0.78'
    environment['PYTHONPATH'] = str(REPO)
    return command, environment

print(f'자동 선택 시드: {BEST_SEED} / 미리보기 없이 전체 영상을 생성합니다.')
"""


FULL_RENDER = r'''# 6. 전체 영상 자동 렌더링, 원본 음성 재결합, Drive 저장, 재생
def media_duration(path):
    return float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
    ]).decode().strip())

audio_duration = media_duration(PADDED_AUDIO)
first_segment_seconds = 93 / 25
following_segment_seconds = (93 - 13) / 25
minimum_segments = max(1, 1 + math.ceil(
    max(0, audio_duration - first_segment_seconds) / following_segment_seconds
))
# 마지막 발화가 경계에서 잘리지 않도록 한 구간을 추가 생성한다.
NUM_SEGMENTS = minimum_segments + 1
print(f'패딩 포함 음성 길이: {audio_duration:.2f}초 / 안전 여유 포함 생성 구간: {NUM_SEGMENTS}')

def run_full_render(render_resolution):
    global RESOLUTION
    RESOLUTION = render_resolution
    render_output = OUTPUT_DIR / f'full_sohee_one_second_pause_v10_seed_{BEST_SEED}_{render_resolution}'
    render_output.mkdir(parents=True, exist_ok=True)
    expected = render_output / ('final_video.mp4' if LOW_VRAM and NUM_SEGMENTS > 1 else 'segment_001.mp4')
    if expected.exists() and expected.stat().st_size > 100_000:
        print(f'이미 완성된 렌더 재사용: {expected}')
        return render_output

    command, environment = avatar_command(
        render_output, BEST_SEED, NUM_SEGMENTS, ref_img_index=0, mask_frame_range=3
    )
    environment['PYTHONUNBUFFERED'] = '1'
    log_path = render_output / 'render.log'
    print(f'\n===== 전체 영상 {render_resolution} 렌더 시작 =====')
    print('진행 상황 및 로그:', log_path)
    with log_path.open('w', encoding='utf-8') as log_file:
        process = subprocess.Popen(
            command, cwd=str(REPO), env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        for line in process.stdout:
            print(line, end='')
            log_file.write(line)
            log_file.flush()
        return_code = process.wait()
    if return_code != 0:
        print(f'{render_resolution} 렌더 실패 (종료 코드 {return_code})')
        return None
    return render_output

full_output = run_full_render('720p')
if full_output is None and LOW_VRAM:
    print('\n720p 렌더 메모리가 40GB를 초과했습니다. 480p로 자동 재시도합니다.')
    full_output = run_full_render('480p')
if full_output is None:
    logs = sorted(OUTPUT_DIR.glob(f'full_sohee_one_second_pause_v10_seed_{BEST_SEED}_*/render.log'), key=lambda p: p.stat().st_mtime)
    if logs:
        last_log = logs[-1]
        drive_log = DRIVE_DIR / 'outputs' / 'last_render_error.log'
        shutil.copy2(last_log, drive_log)
        tail = last_log.read_text(encoding='utf-8', errors='replace').splitlines()[-80:]
        print('\n===== 렌더 실패 마지막 80줄 =====')
        print('\n'.join(tail))
        print('전체 로그 Drive 저장:', drive_log)
    raise RuntimeError('720p와 480p 전체 렌더가 모두 실패했습니다. 위 오류를 확인해주세요.')

if LOW_VRAM:
    generated_final = full_output / ('final_video.mp4' if NUM_SEGMENTS > 1 else 'segment_001.mp4')
else:
    continued = list(full_output.glob('video_continue_*.mp4'))
    if continued:
        def segment_number(path):
            match = re.search(r'video_continue_(\d+)', path.stem)
            return int(match.group(1)) if match else 0
        generated_final = max(continued, key=segment_number)
    else:
        generated_final = full_output / 'ai2v_demo_1.mp4'

if not generated_final.exists():
    raise FileNotFoundError(f'생성 영상을 찾지 못했습니다: {generated_final}')

# LongCat이 넣은 임시 오디오를 사용하지 않는다. 영상이 짧을 경우 마지막 프레임을
# 필요한 만큼만 연장한 뒤, 누락 없는 원본 패딩 WAV를 다시 결합한다.
video_duration = media_duration(generated_final)
extension = max(0.0, audio_duration - video_duration + 0.08)
LOCAL_FINAL = OUTPUT_DIR / 'lee_jieun_longcat15_v10_sohee_one_second_pause_restrained_mouth.mp4'
subprocess.run([
    'ffmpeg', '-y', '-v', 'warning',
    '-i', str(generated_final), '-i', str(PADDED_AUDIO),
    '-filter_complex', f'[0:v]tpad=stop_mode=clone:stop_duration={extension:.3f}[v]',
    '-map', '[v]', '-map', '1:a:0',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-t', f'{audio_duration:.3f}',
    '-movflags', '+faststart', str(LOCAL_FINAL)
], check=True)

final_duration = media_duration(LOCAL_FINAL)
if final_duration + 0.15 < audio_duration:
    raise RuntimeError(f'최종 영상 길이 검증 실패: 영상 {final_duration:.2f}초 / 음성 {audio_duration:.2f}초')

DRIVE_FINAL = DRIVE_DIR / 'outputs' / LOCAL_FINAL.name
shutil.copy2(LOCAL_FINAL, DRIVE_FINAL)
print(f'\n완료: {DRIVE_FINAL}')
print(f'최종 길이: {final_duration:.2f}초 / 크기: {DRIVE_FINAL.stat().st_size / 1024**2:.1f} MB')
display(Video(str(DRIVE_FINAL), embed=False, width=1000))
'''


AUDIO_DRIVE_PATCH = r'''# v1.5 distill의 오디오 구동 강도를 낮춰 입·턱 움직임의 과장을 줄인다.
# 음성 WAV의 볼륨이나 음색은 바꾸지 않고 영상 생성 조건의 강도만 조절한다.
def patch_audio_guidance(source):
    original = "audio_guidance_scale = 1.0"
    controlled = (
        "audio_guidance_scale = float(os.environ.get("
        "'LONGCAT_AUDIO_GUIDANCE_SCALE', '0.78'))"
    )
    if original in source:
        source = source.replace(original, controlled, 1)
    if controlled not in source:
        raise RuntimeError('LongCat 오디오 구동 강도 패치 위치를 찾지 못했습니다.')
    return source

script_path.write_text(
    patch_audio_guidance(script_path.read_text(encoding='utf-8')),
    encoding='utf-8',
)
lowmem_text = patch_audio_guidance(lowmem_text)
print('입모양 억제용 오디오 구동 강도:', os.environ.get('LONGCAT_AUDIO_GUIDANCE_SCALE', '0.78'))
'''


def replace_once(source: str, old: str, new: str, *, label: str) -> str:
    if old not in source:
        raise RuntimeError(f"{label}: expected text not found: {old!r}")
    return source.replace(old, new, 1)


def main() -> None:
    for target in TARGETS:
        notebook = json.loads(target.read_text(encoding="utf-8"))
        cells = {cell.get("id"): cell for cell in notebook["cells"]}

        cells["intro"]["source"] = source_lines(INTRO)
        cells["mount-upload"]["source"] = source_lines(MOUNT_IMAGE)

        install = cells["install-download"]
        install_source = "".join(install["source"])
        install_source = install_source.replace(
            "# 2. 공식 코드와 전용 Python 3.10 환경 설치, 필요한 가중치만 다운로드",
            "# 3. LongCat 공식 코드와 전용 Python 3.10 환경 설치, 필요한 가중치만 다운로드",
            1,
        )
        install_source = install_source.replace("torch==2.6.0+cu124", "torch==2.6.0")
        install_source = install_source.replace("torchvision==0.21.0+cu124", "torchvision==0.21.0")
        install_source = install_source.replace("torchaudio==2.6.0+cu124", "torchaudio==2.6.0")
        install_source = install_source.replace(
            "'--index-url', 'https://download.pytorch.org/whl/cu124'",
            "'--extra-index-url', 'https://download.pytorch.org/whl/cu124', "
            "'--index-strategy', 'unsafe-best-match'",
        )
        if "# 3. LongCat 공식 코드" not in install_source:
            raise RuntimeError(f"{target.name}: LongCat 설치 셀 제목을 찾지 못했습니다.")
        install["source"] = source_lines(install_source)

        prepare = cells["prepare-job"]
        prepare_source = "".join(prepare["source"])
        prepare_source = prepare_source.replace(
            "# 3. 자연스러운 상담 장면 지시문과 실행 작업 생성",
            "# 4. 자연스러운 상담 장면 지시문과 실행 작업 생성",
            1,
        )
        if "# 4. 자연스러운 상담 장면" not in prepare_source:
            raise RuntimeError(f"{target.name}: 영상 지시문 셀 제목을 찾지 못했습니다.")
        if "def patch_audio_guidance(source):" not in prepare_source:
            anchor = "LOWMEM_SCRIPT.write_text(lowmem_text, encoding='utf-8')"
            prepare_source = replace_once(
                prepare_source,
                anchor,
                AUDIO_DRIVE_PATCH + "\n" + anchor,
                label=target.name,
            )
        prepare["source"] = source_lines(prepare_source)

        preview = cells.get("preview") or cells["automatic-render-config"]
        preview["id"] = "automatic-render-config"
        preview["source"] = source_lines(AUTO_CONFIG)

        cells["full-render"]["source"] = source_lines(FULL_RENDER)

        download = cells["download"]
        download_source = "".join(download["source"])
        download_source = download_source.replace(
            "# 6. 선택 사항: 최종 MP4를 현재 PC로 다운로드",
            "# 7. 선택 사항: 최종 MP4를 현재 PC로 다운로드",
            1,
        )
        if "# 7. 선택 사항: 최종 MP4" not in download_source:
            raise RuntimeError(f"{target.name}: 다운로드 셀 제목을 찾지 못했습니다.")
        download["source"] = source_lines(download_source)

        auto_tts_cell = {
            "cell_type": "code",
            "execution_count": None,
            "id": "auto-qwen-tts",
            "metadata": {},
            "outputs": [],
            "source": source_lines(AUTO_TTS),
        }
        ordered = []
        for cell in notebook["cells"]:
            if cell.get("id") == "auto-qwen-tts":
                continue
            cell["execution_count"] = None if cell.get("cell_type") == "code" else cell.get("execution_count")
            if cell.get("cell_type") == "code":
                cell["outputs"] = []
            ordered.append(cell)
            if cell.get("id") == "mount-upload":
                ordered.append(auto_tts_cell)
        notebook["cells"] = ordered
        notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = target.name
        code_sources = [
            "".join(cell["source"])
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        ]
        for index, code_source in enumerate(code_sources):
            ast.parse(code_source, filename=f"{target.name}:code-cell-{index}")
        combined_code = "\n".join(code_sources)
        if any(value in combined_code for value in ("files.upload", "input(", "PREVIEW_SEEDS")):
            raise RuntimeError(f"{target.name}: 수동 입력 코드가 남아 있습니다.")
        if "embedded_image_base64" in combined_code or "__EMBEDDED_SOURCE_IMAGE_BASE64__" in combined_code:
            raise RuntimeError(f"{target.name}: Base64 내장 이미지가 남아 있습니다.")
        if "speaker=['Sohee']" not in combined_code:
            raise RuntimeError(f"{target.name}: 한국어 여성 Sohee 화자가 고정되지 않았습니다.")
        target.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(target, "ZERO_INPUT_COMPILE_OK")


if __name__ == "__main__":
    main()
