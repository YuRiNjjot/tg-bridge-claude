# tg-bridge-claude

Telegram bridge для Claude Code. Общайся с Claude Code через Telegram — как с обычным агентом.

**Bridge = мост, не самостоятельный AI-чат.** AI-ответы даёт Claude Code, а не bridge.

---

## Быстрый старт (три шага)

### 1. Клонируй

```powershell
git clone https://github.com/YuRiNjjot/tg-bridge-claude.git
cd tg-bridge-claude
```

### 2. Запусти Claude Code в папке

```powershell
claude
```

### 3. Скажи Claude Code запустить bridge

Напиши Claude Code:

> "запусти bridge" или "вот путь до скрипта: .\launch_bridge.ps1"

Claude Code сам:
- Установит зависимости (`pip install`)
- Создаст `.env` из `.env.example` (попросит заполнить токен)
- Пропишет auto-approve в `settings.json`
- Запустит `bridge_bot` в фоне + `bridge_poller` в терминале

---

## Как это работает

```
[Ты в Telegram] → bridge_bot.py → bridge_messages.jsonl
                                                 ↓
                              [Claude Code читает и отвечает]
                                                 ↓
                                    bridge_outbox.jsonl
                                                 ↓
                              bridge_bot.py → [Ты в Telegram]
```

1. Пишешь в Telegram (текст или голосовое)
2. `bridge_bot.py` логирует в `bridge_messages.jsonl`
3. `bridge_poller.py` показывает Claude Code уведомление в терминале
4. Claude Code пишет ответ в `bridge_outbox.jsonl`
5. `bridge_bot.py` отправляет ответ в Telegram

---

## Требования

- **Windows 11** (native)
- **Python 3.10+** (установлен)
- **Claude Code** (CLI, уже установлен)
- **ffmpeg** (опционально, для голосовых)

Остальное Claude Code сделает сам.

---

## Файлы

| Файл | Назначение |
|------|-----------|
| `bridge_bot.py` | Daemon: polling Telegram API, whisper Vulkan, отправка outbox |
| `bridge_poller.py` | ANSI-монитор для Claude Code (яркие баннеры при новом сообщении) |
| `launch_bridge.ps1` | **Точка входа** — убивает старые процессы, запускает bridge + poller |
| `config.py` | Чтение `.env` и валидация |
| `.env.example` | Шаблон конфигурации |

---

## Команды Telegram

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/id` | Узнать chat_id |
| `/bash <cmd>` | Выполнить команду (sandbox) |
| `/ls [path]` | Список файлов |
| `/cd <path>` | Сменить директорию |
| `/pwd` | Текущая директория |

---

## Триггер: "запустибридж"

Если bridge упал — напиши в Telegram или чат Claude Code **"запустибридж"**. Claude Code автоматически перезапустит bridge без ручных действий.

---

## Голосовые сообщения

Bridge использует **локальный** whisper.cpp с Vulkan backend (AMD RX 6900 XT). Никаких облачных API не нужно.

Если whisper не найден — голосовые помечаются как `[VOICE - failed to transcribe]`, но текстовые продолжают работать.

---

## Лицензия

MIT
