# tg-bridge-claude

Telegram bridge для Claude Code. Позволяет общаться с Claude Code через Telegram — как с обычным агентом.

**Bridge = мост, а не самостоятельный AI-чат.** AI-ответы даёт Claude Code, а не bridge.

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

1. Ты пишешь в Telegram (текст или голосовое)
2. `bridge_bot.py` логирует сообщение в `bridge_messages.jsonl`
3. `bridge_poller.py` показывает Claude Code уведомление в терминале
4. Claude Code пишет ответ в `bridge_outbox.jsonl`
5. `bridge_bot.py` отправляет ответ в Telegram

---

## Требования

- **Windows 11** (native, без WSL)
- **Python 3.10+**
- **ffmpeg** (для конвертации голосовых) — `winget install ffmpeg`
- **whisper.cpp с Vulkan** (для GPU AMD RX 6900 XT, или аналог)
- **Claude Code** (CLI)

---

## Быстрый старт

### 1. Клонируй репозиторий

```powershell
git clone https://github.com/YuRiNjjot/tg-bridge-claude.git
cd tg-bridge-claude
```

### 2. Установи зависимости

```powershell
pip install -r requirements.txt
```

### 3. Настрой `.env`

Скопируй пример:

```powershell
cp .env.example .env
```

Отредактируй `.env`:

```env
# Получить токен у @BotFather в Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Твой Telegram ID (узнать через @userinfobot)
ADMIN_TG_ID=your_telegram_user_id_here

# Пути для whisper.cpp (уже настроены для AMD + Vulkan)
WHISPER_WINDOWS_EXE=D:\\ai\\audio-text\\whisper-vulkan\\whisper-cli.exe
WHISPER_WINDOWS_MODEL=D:\\AI\\hermes\\whisper-bin\\ggml-small.bin
WHISPER_WINDOWS_TEMP=D:\\tmp\\tg-claude
```

### 4. Запусти bridge

```powershell
.\launch_bridge.ps1
```

Что делает скрипт:
1. Убивает старые процессы `bridge_bot.py`
2. Запускает `bridge_bot.py` в фоне (через `pythonw`, без консольного окна)
3. Запускает `bridge_poller.py` в терминале для мониторинга

### 5. Пиши в Telegram

Bridge готов. Отправь сообщение в Telegram — Claude Code увидит его и ответит.

---

## Архитектура

### Bridge = мост, не зеркало

В отличие от других Telegram-ботов, этот bridge **не отвечает сам**. Он только:
- Логирует входящие сообщения
- Транскрибирует голосовые (whisper.cpp + Vulkan)
- Отправляет ответы, которые написал Claude Code

AI-ответы всегда идут через Claude Code.

### Файлы

| Файл | Назначение |
|------|-----------|
| `bridge_bot.py` | Daemon: polling Telegram API, логирование, отправка ответов |
| `bridge_poller.py` | ANSI-монитор для Claude Code (яркие баннеры при новом сообщении) |
| `bridge_reader.py` | Утилита чтения bridge_messages.jsonl |
| `bridge_monitor.py` | Старый простой монитор (без ANSI) |
| `config.py` | Чтение `.env` и валидация конфигурации |
| `send_tg.py` | Утилита отправки сообщения в Telegram |
| `launch_bridge.ps1` | Единый скрипт запуска |

### Данные

| Файл | Содержимое |
|------|-----------|
| `data/bridge_messages.jsonl` | Входящие сообщения из Telegram |
| `data/bridge_outbox.jsonl` | Исходящие ответы от Claude Code |
| `data/.poller_state` | ID последнего обработанного сообщения |

---

## Whisper.cpp + Vulkan (AMD GPU)

Bridge использует **локальный** whisper.cpp с Vulkan backend для транскрибации голосовых. Никаких облачных API не нужно.

**Проверено на:** AMD RX 6900 XT 16GB, Windows 11.

Если у тебя NVIDIA — используй CUDA-сборку whisper.cpp. Если CPU — используй CPU-сборку.

---

## Команды Telegram

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/id` | Узнать свой chat_id и user_id |
| `/bash <cmd>` | Выполнить команду в терминале (sandbox: только разрешённые пути) |
| `/ls [path]` | Список файлов |
| `/cd <path>` | Сменить рабочую директорию |
| `/pwd` | Текущая директория |

---

## Claude Code: auto-approve bridge

Чтобы Claude Code не спрашивал разрешение на запуск bridge-скриптов, добавь в `settings.json`:

```json
{
  "permissions": {
    "defaultMode": "auto",
    "allow": [
      "Bash(*bridge_bot.py*)",
      "Bash(*bridge_poller.py*)",
      "Bash(*launch_bridge.ps1*)",
      "Bash(*python*)",
      "PowerShell(*)",
      "Edit(*bridge_outbox.jsonl*)",
      "Write(*bridge_outbox.jsonl*)"
    ]
  }
}
```

---

## Триггер: "запустибридж"

Если bridge упал, напиши в Telegram (или в чат Claude Code) команду **"запустибридж"**. Claude Code автоматически:
1. Убьёт старые процессы
2. Запустит bridge_bot в фоне
3. Запустит poller в терминале

---

## Лицензия

MIT
