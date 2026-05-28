#!/usr/bin/env python3
"""
Bridge Poller — автоматический монитор новых Telegram сообщений.

Запускай в терминале рядом с Claude Code:
    python bridge_poller.py

При новом сообщении выводит яркое уведомление в stdout,
чтобы Claude Code увидел его в своём терминале.
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "bridge_messages.jsonl"
STATE_FILE = DATA_DIR / ".poller_state"
OUT_FILE = DATA_DIR / "bridge_outbox.jsonl"

# ANSI colors (работают в PowerShell 7+ и новых терминалах Windows)
CLR = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _color(text, color):
    """Добавить ANSI-цвет к тексту."""
    if sys.platform == "win32" and os.environ.get("TERM") is None:
        return text
    return f"{CLR.get(color, '')}{text}{CLR['reset']}"


def _load_last_id():
    if STATE_FILE.exists():
        try:
            return int(STATE_FILE.read_text().strip())
        except ValueError:
            pass
    return 0


def _save_last_id(uid):
    STATE_FILE.write_text(str(uid))


def _poll():
    last_id = _load_last_id()
    new_messages = []

    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    uid = msg.get("update_id", 0)
                    if uid > last_id:
                        new_messages.append(msg)
                        last_id = max(last_id, uid)
                except json.JSONDecodeError:
                    continue

    if new_messages:
        _save_last_id(last_id)
    return new_messages


def _print_banner(msg):
    """Печать яркого уведомления о новом сообщении."""
    name = msg.get("username") or msg.get("first_name") or "Unknown"
    text = msg.get("text", "")
    voice = msg.get("voice_transcript")
    photo = msg.get("photo_path")
    msg_id = msg.get("message_id", 0)
    chat_id = msg.get("chat_id", 0)

    if voice:
        text = f"[VOICE] {voice}"
    elif photo:
        text = f"[PHOTO] {photo}"

    print("")
    print(_color("╔" + "=" * 70 + "╗", "yellow"), flush=True)
    print(_color("║" + " NEW TELEGRAM MESSAGE ".center(70) + "║", "yellow"), flush=True)
    print(_color("╠" + "=" * 70 + "╣", "yellow"), flush=True)
    print(_color(f"║ From: {name} (chat={chat_id}, msg={msg_id})".ljust(72) + "║", "cyan"), flush=True)
    print(_color(f"║ Time: {msg.get('time', 'unknown')}".ljust(72) + "║", "cyan"), flush=True)
    print(_color("╠" + "-" * 70 + "╣", "yellow"), flush=True)

    max_len = 68
    text_lines = []
    while len(text) > max_len:
        idx = text.rfind(" ", 0, max_len)
        if idx == -1:
            idx = max_len
        text_lines.append(text[:idx])
        text = text[idx:].strip()
    if text:
        text_lines.append(text)

    for line in text_lines:
        print(_color(f"║ {line}".ljust(72) + "║", "bold"), flush=True)

    print(_color("╚" + "=" * 70 + "╝", "yellow"), flush=True)
    print("")
    print(_color("[POLLER] Claude Code: reply via bridge_outbox.jsonl", "green"), flush=True)
    print(_color(f"[POLLER] python -c \"import json; open('{OUT_FILE}','a').write(json.dumps({{'chat_id':{chat_id},'text':'Ответ','reply_to':{msg_id}}},ensure_ascii=False)+'\\n')\"", "green"), flush=True)
    print("")


def main():
    print(_color("[BRIDGE POLLER] Watching for new messages...", "green"), flush=True)
    print(_color(f"[BRIDGE POLLER] Log: {LOG_FILE}", "cyan"), flush=True)
    print(_color("[BRIDGE POLLER] Poll interval: 3s | Press Ctrl+C to stop\n", "cyan"), flush=True)

    tick = 0
    while True:
        try:
            messages = _poll()
            if messages:
                for msg in messages:
                    _print_banner(msg)
            else:
                # Heartbeat каждые 10 тиков (~30 сек) чтобы показать что жив
                tick += 1
                if tick % 10 == 0:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"[POLLER {now}] No new messages...", flush=True)

            time.sleep(3)
        except KeyboardInterrupt:
            print(_color("\n[BRIDGE POLLER] Stopped.", "red"), flush=True)
            break
        except Exception as e:
            print(_color(f"[BRIDGE POLLER ERROR] {e}", "red"), flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
