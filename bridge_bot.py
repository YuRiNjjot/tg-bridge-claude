#!/usr/bin/env python3
"""
Telegram Bridge Bot — Claude Code reads messages, writes replies.
Uses GPU whisper (AMD RX 6900 XT via Vulkan) for voice transcription.

IN:  Telegram messages → bridge_messages.log
OUT: bridge_outbox.jsonl → Telegram
"""

import os
import sys
import json
import time
import shutil
import requests
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent dir to path for config import
sys.path.insert(0, str(Path(__file__).parent))
import config

# === CONFIG ===
TOKEN = config.TELEGRAM_BOT_TOKEN
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = str(DATA_DIR / "bridge_messages.jsonl")
OUT_FILE = str(DATA_DIR / "bridge_outbox.jsonl")
VOICE_DIR = str(DATA_DIR / "voice")
PHOTO_DIR = str(DATA_DIR / "photos")

# Whisper paths from config (supports AMD Vulkan + NVIDIA/CPU)
WIN_WHISPER = config.WHISPER_WINDOWS_EXE or r"D:\ai\audio-text\whisper-vulkan\whisper-cli.exe"
WIN_MODEL = config.WHISPER_WINDOWS_MODEL or r"D:\AI\hermes\whisper-bin\ggml-small.bin"
WIN_TEMP = config.WHISPER_WINDOWS_TEMP or r"D:\tmp\tg-claude"

STATE_FILE = str(DATA_DIR / ".bridge_state")
CWD_FILE = str(DATA_DIR / ".bridge_cwd")

# Allowed directories for bash commands (security)
ALLOWED_ROOTS = [str(BASE_DIR), "D:\\", "C:\\"]

def _load_last_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip() or 0)
    return 0

def _save_last_id(uid):
    with open(STATE_FILE, "w") as f:
        f.write(str(uid))

LAST_UPDATE_ID = _load_last_id()

# Track current working directory for bash commands
def _get_cwd():
    if os.path.exists(CWD_FILE):
        with open(CWD_FILE, "r") as f:
            cwd = f.read().strip()
            if os.path.isdir(cwd):
                return cwd
    return str(BASE_DIR)

def _set_cwd(cwd):
    with open(CWD_FILE, "w") as f:
        f.write(cwd)

def _is_path_allowed(path):
    """Security check: path must be within allowed roots."""
    abs_path = os.path.abspath(path)
    for root in ALLOWED_ROOTS:
        if abs_path.startswith(os.path.abspath(root)):
            return True
    return False

def _run_bash(command, cwd):
    """Execute bash command safely."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]: " + result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output[:3800]  # Telegram limit ~4096, leave room
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out after 30 seconds"
    except Exception as e:
        return f"[ERROR] {e}"

def _format_ls(path, cwd):
    """List files in directory."""
    target = os.path.join(cwd, path) if path else cwd
    target = os.path.abspath(target)
    if not _is_path_allowed(target):
        return "[ERROR] Path not allowed"
    if not os.path.exists(target):
        return f"[ERROR] Path does not exist: {target}"
    try:
        items = os.listdir(target)
        lines = [f"Contents of {target}:"]
        for item in sorted(items):
            full = os.path.join(target, item)
            if os.path.isdir(full):
                lines.append(f"  📁 {item}/")
            else:
                size = os.path.getsize(full)
                lines.append(f"  📄 {item} ({size} bytes)")
        return "\n".join(lines[:100])  # Limit output
    except Exception as e:
        return f"[ERROR] {e}"

def _handle_command(text, chat_id, reply_to):
    """Handle terminal commands from Telegram. Returns True if handled."""
    cwd = _get_cwd()

    if text.startswith("/cd "):
        new_path = text[4:].strip()
        target = os.path.abspath(os.path.join(cwd, new_path))
        if not _is_path_allowed(target):
            send_message(chat_id, f"[ERROR] Path not allowed: {target}", reply_to)
            return True
        if os.path.isdir(target):
            _set_cwd(target)
            send_message(chat_id, f"📂 Changed to: {target}", reply_to)
        else:
            send_message(chat_id, f"[ERROR] Not a directory: {target}", reply_to)
        return True

    elif text == "/pwd":
        send_message(chat_id, f"📂 Current: {cwd}", reply_to)
        return True

    elif text.startswith("/ls"):
        path = text[3:].strip() if len(text) > 3 else ""
        output = _format_ls(path, cwd)
        send_message(chat_id, f"```{output}```" if not output.startswith("[ERROR]") else output, reply_to)
        return True

    elif text.startswith("/bash "):
        command = text[6:].strip()
        if not command:
            send_message(chat_id, "Usage: /bash <command>", reply_to)
            return True
        output = _run_bash(command, cwd)
        send_message(chat_id, f"```\n{output}\n```"[:4096], reply_to)
        return True

    return False

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(WIN_TEMP, exist_ok=True)


def send_message(chat_id, text, reply_to=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:4096]}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"[ERROR] send_message: {e}")
        return None


def get_updates(offset=0):
    try:
        resp = requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset, "limit": 10}, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"[ERROR] get_updates: {e}")
        return {"ok": False}


def transcribe_voice(voice, chat_id, msg_id):
    """Download voice, convert to WAV, transcribe via GPU whisper."""
    try:
        file_id = voice["file_id"]
        resp = requests.get(f"{BASE_URL}/getFile?file_id={file_id}", timeout=30)
        data = resp.json()
        if not data.get("ok"):
            return None

        file_path = data["result"]["file_path"]
        ext = os.path.splitext(file_path)[1] or ".ogg"
        local_name = f"voice_{chat_id}_{msg_id}_{int(time.time())}{ext}"
        local_path = os.path.join(VOICE_DIR, local_name)

        dl_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        r = requests.get(dl_url, timeout=60)
        with open(local_path, "wb") as f:
            f.write(r.content)

        # Convert to WAV
        wav_path = local_path.replace(ext, ".wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", local_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path],
            capture_output=True, check=True, timeout=30
        )

        # Copy to Windows temp for GPU whisper
        win_wav = os.path.join(WIN_TEMP, os.path.basename(wav_path))
        shutil.copy(wav_path, win_wav)

        # Run Windows whisper-cli.exe directly (native Windows, no WSL)
        t0 = time.time()
        result = subprocess.run(
            [WIN_WHISPER, "-m", WIN_MODEL, "-f", win_wav, "-np", "-l", "auto"],
            capture_output=True, text=True, timeout=120,
        )
        elapsed = time.time() - t0

        # Cleanup
        os.remove(local_path)
        os.remove(wav_path)
        os.remove(win_wav)

        # Parse output
        lines = result.stdout.strip().split("\n")
        text_parts = []
        for line in lines:
            if "]" in line:
                parts = line.split("]", 1)
                if len(parts) > 1 and parts[1].strip():
                    text_parts.append(parts[1].strip())

        transcript = " ".join(text_parts) if text_parts else result.stdout.strip() or None
        print(f"[WHISPER] GPU transcribed in {elapsed:.2f}s: {transcript[:60] if transcript else 'FAILED'}")
        return transcript

    except Exception as e:
        print(f"[ERROR] transcribe_voice: {e}")
        return None


def download_photo(photo, chat_id, msg_id):
    """Download photo from Telegram and save to disk."""
    try:
        # Get the largest photo size
        file_id = photo[-1]["file_id"] if isinstance(photo, list) else photo["file_id"]
        resp = requests.get(f"{BASE_URL}/getFile?file_id={file_id}", timeout=30)
        data = resp.json()
        if not data.get("ok"):
            return None

        file_path = data["result"]["file_path"]
        ext = os.path.splitext(file_path)[1] or ".jpg"
        local_name = f"photo_{chat_id}_{msg_id}_{int(time.time())}{ext}"
        local_path = os.path.join(PHOTO_DIR, local_name)

        dl_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        r = requests.get(dl_url, timeout=60)
        with open(local_path, "wb") as f:
            f.write(r.content)

        print(f"[PHOTO] Downloaded: {local_path}")
        return local_path
    except Exception as e:
        print(f"[ERROR] download_photo: {e}")
        return None


def log_incoming(update):
    msg = update.get("message", {})
    chat = msg.get("chat", {})
    from_user = msg.get("from", {})

    entry = {
        "time": datetime.now().isoformat(),
        "update_id": update.get("update_id"),
        "chat_id": chat.get("id"),
        "user_id": from_user.get("id"),
        "username": from_user.get("username"),
        "first_name": from_user.get("first_name"),
        "text": msg.get("text", ""),
        "message_id": msg.get("message_id"),
    }

    # Handle voice
    if "voice" in msg:
        transcript = transcribe_voice(msg["voice"], chat.get("id"), msg.get("message_id"))
        entry["voice_transcript"] = transcript
        entry["text"] = transcript or "[VOICE - failed to transcribe]"

    # Handle photo
    if "photo" in msg:
        photo_path = download_photo(msg["photo"], chat.get("id"), msg.get("message_id"))
        if photo_path:
            entry["photo_path"] = photo_path
            entry["text"] = f"[PHOTO] Saved to: {photo_path}"
        else:
            entry["text"] = "[PHOTO - failed to download]"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Создать файл-флаг для Claude Code
    flag_file = os.path.join(os.path.dirname(LOG_FILE), ".new_message")
    with open(flag_file, "w") as f:
        f.write(str(entry.get("message_id", 0)))

    display = entry["text"][:80] if len(entry["text"]) <= 80 else entry["text"][:77] + "..."
    print(f"[IN] {entry['time']} | {entry.get('username') or entry.get('first_name')}: {display}")


def process_outbox():
    if not os.path.exists(OUT_FILE):
        return

    with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    if not lines:
        return

    failed_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            chat_id = data.get("chat_id")
            text = data.get("text", "")
            reply_to = data.get("reply_to")
            if chat_id and text:
                result = send_message(chat_id, text, reply_to)
                if result and result.get("ok"):
                    print(f"[OUT] -> chat {chat_id}: {text[:60]}")
                else:
                    print(f"[WARN] send failed, keeping: {result}")
                    failed_lines.append(json.dumps(data, ensure_ascii=False) + "\n")
            else:
                failed_lines.append(line + "\n")
        except Exception as e:
            print(f"[ERROR] outbox: {e}")
            failed_lines.append(line + "\n")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(failed_lines)


def main_loop():
    global LAST_UPDATE_ID
    print(f"[BRIDGE] Bot started. Token: {TOKEN[:10]}...")
    print(f"[BRIDGE] Log: {LOG_FILE}")
    print(f"[BRIDGE] Outbox: {OUT_FILE}")
    print(f"[BRIDGE] Waiting for messages...")

    while True:
        try:
            data = get_updates(offset=LAST_UPDATE_ID + 1)
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    LAST_UPDATE_ID = max(LAST_UPDATE_ID, update.get("update_id", 0))
                    msg = update.get("message", {})
                    from_user = msg.get("from", {})
                    text = msg.get("text", "")

                    # Skip messages from the bot itself (echo)
                    if from_user.get("is_bot"):
                        continue

                    if text == "/start":
                        send_message(msg["chat"]["id"],
                            "Bridge online. Messages logged. Claude reads and replies.")
                    elif text == "/id":
                        send_message(msg["chat"]["id"],
                            f"Chat ID: `{msg['chat']['id']}`\nUser ID: `{msg['from']['id']}`",
                            reply_to=msg["message_id"])
                    elif _handle_command(text, msg["chat"]["id"], msg["message_id"]):
                        pass  # Command handled, don't log
                    else:
                        log_incoming(update)

                _save_last_id(LAST_UPDATE_ID)

            process_outbox()
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n[BRIDGE] Stopped.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main_loop()
