#!/usr/bin/env python3
"""
Helper for Claude Code to read bridge messages and send replies.

Usage:
    python bridge_reader.py              # Show new messages
    python bridge_reader.py --reply    # Interactive reply mode
"""
import json
import sys
import os

LOG_FILE = "/mnt/e/ClaudeCode/tg-claude/data/bridge_messages.jsonl"
OUT_FILE = "/mnt/e/ClaudeCode/tg-claude/data/bridge_outbox.jsonl"
STATE_FILE = "/mnt/e/ClaudeCode/tg-claude/data/.last_read"


def get_new_messages():
    """Read messages that haven't been seen yet."""
    last_id = 0
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_id = int(f.read().strip() or 0)

    messages = []
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
                        messages.append(msg)
                        last_id = max(last_id, uid)
                except json.JSONDecodeError:
                    continue

    with open(STATE_FILE, "w") as f:
        f.write(str(last_id))

    return messages


def show_messages(messages):
    if not messages:
        print("No new messages.")
        return

    for msg in messages:
        name = msg.get("username") or msg.get("first_name") or "Unknown"
        text = msg.get("text", "")
        voice = msg.get("voice_transcript")
        if voice:
            text = f"[VOICE] {voice}"
        print(f"\n[{msg['time']}] {name} (chat={msg['chat_id']}, msg={msg['message_id']}):")
        print(f"  {text}")


def send_reply(chat_id, text, reply_to=None):
    """Write reply to outbox for bridge_bot to send."""
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "chat_id": chat_id,
            "text": text,
            "reply_to": reply_to
        }, ensure_ascii=False) + "\n")
    print(f"Reply queued for chat {chat_id}")


def interactive_reply(messages):
    if not messages:
        return

    for msg in messages:
        name = msg.get("username") or msg.get("first_name") or "Unknown"
        text = msg.get("text", "")
        print(f"\nReply to: {name} -> {text[:60]}")
        reply = input("Your reply (empty to skip): ").strip()
        if reply:
            send_reply(msg["chat_id"], reply, msg["message_id"])


if __name__ == "__main__":
    messages = get_new_messages()

    if "--reply" in sys.argv:
        interactive_reply(messages)
    else:
        show_messages(messages)
