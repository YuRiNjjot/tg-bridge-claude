#!/usr/bin/env python3
"""Прямая отправка сообщений в Telegram без подтверждения.

Форматирование:
- Используйте списки с пустыми строками для разделения абзацев
- Markdown поддерживается: **bold**, `code`, списки
- Эмодзи для структуры: 1️⃣ 2️⃣ 3️⃣ ✅ ⚠️ ❌
- Не используйте экранированные \\n — только реальные переносы строк

Пример правильного сообщения:
    lines = [
        "✅ Готово!",
        "",
        "1️⃣ Пункт первый",
        "2️⃣ Пункт второй",
        "",
        "Заключение..."
    ]
    text = "\\n".join(lines)
    send_message(text)
"""
import sys
import requests
import config

BASE_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
CHAT_ID = config.ADMIN_TG_ID


def send_message(text, reply_to=None, parse_mode="Markdown"):
    """Отправить сообщение в Telegram.

    Args:
        text: Текст сообщения. Используйте реальные \\n для переносов.
        reply_to: ID сообщения для reply (опционально).
        parse_mode: "Markdown" или None для plain text.
    """
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text[:4096]}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        if data.get("ok"):
            print(f"Sent to Telegram: {text[:60]}")
            return True
        else:
            print(f"Error: {data}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def format_message(lines):
    """Собрать сообщение из списка строк с правильными переносами.

    Args:
        lines: Список строк. Пустая строка "" создаёт разделитель абзаца.

    Returns:
        str: Отформатированный текст для отправки.
    """
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_tg.py 'Your message'")
        print("")
        print("For multi-line messages:")
        print('  python -c "import send_tg; send_tg.send_message(\\"Line 1\\n\\nLine 2\\")"')
        sys.exit(1)
    send_message(sys.argv[1])
