"""Транскрибация голосовых сообщений через GPU (AMD RX 6900 XT Vulkan).

Приоритет:
1. Windows whisper-cli.exe через cmd.exe (GPU Vulkan)
2. Linux whisper-cli CPU (fallback)
3. OpenAI Whisper API (cloud fallback)
"""
import os
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Optional
import requests
import config

# Windows GPU пути (работает через cmd.exe, использует AMD RX 6900 XT)
WIN_WHISPER = "D:\\ai\\audio-text\\whisper-vulkan\\whisper-cli.exe"
WIN_MODEL = "D:\\AI\\hermes\\whisper-bin\\ggml-small.bin"
WIN_TEMP_DIR = "D:\\tmp\\tg-claude"

# Linux CPU fallback
LINUX_WHISPER = Path("/mnt/e/ClaudeCode/whisper-vulkan/build_cpu/bin/whisper-cli")
LINUX_MODEL = Path("/mnt/e/ClaudeCode/whisper-vulkan/models/for-tests-ggml-small.bin")


def _ensure_win_temp():
    """Создаёт Windows-временную папку."""
    os.makedirs(f"/mnt/d/tmp/tg-claude", exist_ok=True)


def convert_ogg_to_wav(ogg_path: Path) -> Path:
    """Конвертирует OGG в WAV 16kHz mono."""
    wav_path = ogg_path.with_suffix(".wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(ogg_path),
        "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path


def _transcribe_gpu(wav_path: Path) -> Optional[str]:
    """Транскрибация через Windows whisper-cli.exe с AMD GPU Vulkan."""
    try:
        _ensure_win_temp()
        # Копируем WAV во временную Windows-папку
        win_wav = Path(f"/mnt/d/tmp/tg-claude/audio_{os.getpid()}.wav")
        import shutil
        shutil.copy(wav_path, win_wav)

        # Запускаем через cmd.exe с Windows-путями
        cmd = [
            "cmd.exe", "/c",
            f'{WIN_WHISPER} -m {WIN_MODEL} -f {WIN_TEMP_DIR}\\audio_{os.getpid()}.wav -np -l auto'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Удаляем временный файл
        win_wav.unlink(missing_ok=True)

        # Парсим stdout — ищем строки вида [00:00:00.000 --> 00:00:02.000]   текст
        lines = result.stdout.strip().split("\n")
        text_parts = []
        for line in lines:
            if "]" in line:
                parts = line.split("]", 1)
                if len(parts) > 1 and parts[1].strip():
                    text_parts.append(parts[1].strip())

        if text_parts:
            return " ".join(text_parts)

        # Если не нашли таймкоды — просто весь stdout
        return result.stdout.strip() or None

    except Exception as e:
        print(f"[Whisper GPU ERROR] {e}")
        return None


def _transcribe_cpu(wav_path: Path) -> Optional[str]:
    """Fallback: Linux CPU whisper-cli."""
    if not LINUX_WHISPER.exists() or not LINUX_MODEL.exists():
        return None

    try:
        cmd = [
            str(LINUX_WHISPER),
            "-m", str(LINUX_MODEL),
            "-f", str(wav_path),
            "-l", "auto",
            "-np",
            "--output-json",
            "-of", str(wav_path.with_suffix("")),
        ]
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/mnt/e/ClaudeCode/whisper-vulkan/build_cpu/src:/mnt/e/ClaudeCode/whisper-vulkan/build_cpu/ggml/src:" + env.get("LD_LIBRARY_PATH", "")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)

        json_path = wav_path.with_suffix(".json")
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            json_path.unlink(missing_ok=True)
            text = " ".join(seg.get("text", "").strip() for seg in data.get("transcription", []))
            return text.strip() if text else None

        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line.startswith("[") and "]" in line:
                return line.split("]", 1)[1].strip()
        return result.stdout.strip() or None

    except Exception as e:
        print(f"[Whisper CPU ERROR] {e}")
        return None


def _transcribe_cloud(wav_path: Path) -> Optional[str]:
    """OpenAI Whisper API fallback."""
    if not config.OPENAI_API_KEY:
        print("[Whisper] OPENAI_API_KEY не задан.")
        return None
    try:
        with open(wav_path, "rb") as f:
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"model": "whisper-1", "language": "auto"},
                timeout=60,
            )
        data = resp.json()
        if "text" in data:
            return data["text"].strip()
        if "error" in data:
            print(f"[Whisper API ERROR] {data['error']}")
            return None
        return None
    except Exception as e:
        print(f"[Whisper API ERROR] {e}")
        return None


def transcribe(audio_path: Path) -> Optional[str]:
    """Распознаёт речь: GPU > CPU > Cloud."""
    wav_path = audio_path
    if audio_path.suffix.lower() == ".ogg":
        wav_path = convert_ogg_to_wav(audio_path)

    try:
        # 1. Пробуем GPU (Windows exe через cmd.exe)
        if config.WHISPER_BACKEND == "local":
            result = _transcribe_gpu(wav_path)
            if result:
                return result
            print("[Whisper] GPU failed, trying CPU...")

            # 2. Fallback: Linux CPU
            result = _transcribe_cpu(wav_path)
            if result:
                return result
            print("[Whisper] CPU failed, trying cloud...")

        # 3. Cloud fallback
        return _transcribe_cloud(wav_path)

    except Exception as e:
        print(f"[Whisper ERROR] {e}")
        return None
    finally:
        if wav_path != audio_path and wav_path.exists():
            wav_path.unlink(missing_ok=True)
