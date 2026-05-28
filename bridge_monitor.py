#!/usr/bin/env python3
"""
Монитор новых сообщений для Claude Code.
Выводит новые сообщения в stdout как они приходят.
"""
import json
import os
import time

from pathlib import Path
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = str(DATA_DIR / "bridge_messages.jsonl")
STATE_FILE = str(DATA_DIR / ".monitor_state")


def get_last_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip() or 0)
    return 0


def save_last_seen(uid):
    with open(STATE_FILE, "w") as f:
        f.write(str(uid))


def poll_messages():
    last_id = get_last_seen()
    new_messages = []

    if os.path.exists(LOG_FILE):
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
        save_last_seen(last_id)
        for msg in new_messages:
            name = msg.get("username") or msg.get("first_name") or "Unknown"
            text = msg.get("text", "")
            voice = msg.get("voice_transcript")
            if voice:
                text = f"[VOICE] {voice}"
            print(f"\n{'='*60}")
            print(f"[NEW MESSAGE] {msg['time']}")
            print(f"From: {name} (chat={msg['chat_id']}, msg={msg['message_id']})")
            print(f"Text: {text}")
            print(f"{'='*60}")

    return len(new_messages)


if __name__ == "__main__":
    print("[MONITOR] Watching for new messages...")
    print(f"[MONITOR] Log file: {LOG_FILE}")
    print("[MONITOR] Press Ctrl+C to stop\n")

    while True:
        try:
            count = poll_messages()
            if count > 0:
                print(f"[MONITOR] {count} new message(s) found")
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n[MONITOR] Stopped.")
            break
        except Exception as e:
            print(f"[MONITOR ERROR] {e}")
            time.sleep(5)
