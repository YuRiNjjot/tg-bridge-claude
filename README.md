# tg-claude — Telegram-бот для общения с AI

Telegram-бот, который принимает текст и голосовые сообщения, отправляет их в AI (OpenRouter/Groq/Ollama) и возвращает ответ. Контекст диалога сохраняется между сессиями.

## Возможности

- **Текст** — отправляй текст, получай ответ от AI
- **Голосовые** — скачивает, конвертирует через ffmpeg, транскрибирует через whisper.cpp (Vulkan/AMD GPU) или OpenAI fallback
- **Multi-provider AI** — авто-fallback: OpenRouter (MiniMax M2.5) → Groq (Mistral) → Ollama (локальный kimi-k2.5:cloud)
- **Персистентный контекст** — история сообщений в SQLite + JSON-синхронизация между папками
- **Авто-approve** — Claude Code не спрашивает разрешений на bash-команды
- **Адаптивный rate limit** — при 429 от одного провайдера переключается на следующий

## Структура

```
tg-claude/
├── bot.py                     # Основной бот
├── config.py                  # Конфигурация из .env
├── llm_client.py             # Multi-provider LLM (OpenRouter → Groq → Ollama)
├── whisper_client.py         # Локальный whisper.cpp (Vulkan) или OpenAI fallback
├── memory.py                 # SQLite хранилище контекста
├── context_persistence.py    # JSON-синхронизация контекста между папками
├── requirements.txt
├── .env                       # Ключи API (не коммитить)
├── .env.example
├── data/                      # SQLite + временные голосовые
│   ├── chat_memory.db
│   └── voice/
├── .claude/
│   ├── settings.json          # Авто-разрешения для Claude Code
│   └── context.json           # Персистентный контекст
└── README.md
```

## Быстрый старт (если открыта новая сессия Claude Code)

> Если ты агент и читаешь это в новой сессии — выполни:

```bash
cd /mnt/e/ClaudeCode/tg-claude
pip install -r requirements.txt   # если .venv не активен
python3 bot.py
```

Если зависимости уже установлены — просто `python3 bot.py`.

**Фоновый режим:**
```bash
nohup python3 bot.py > bot.log 2>&1 &
echo $! > bot.pid
```

**Остановить:** `kill $(cat bot.pid)`

**Логи:** `tail -f bot.log`

## Установка с нуля

### 1. Переменные окружения

Файл `.env` уже заполнен ключами. Если нужно поменять:

```bash
cp .env.example .env
```

Поля:
```
TELEGRAM_BOT_TOKEN=            # Токен от @BotFather (получить обязательно)
OPENROUTER_API_KEY=sk-or-...   # Уже заполнен (MiniMax M2.5 Free)
GROQ_API_KEY=gsk_...           # Уже заполнен (Mistral fallback)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=kimi-k2.5:cloud
WHISPER_BACKEND=local          # local (Vulkan) или openai (cloud fallback)
OPENAI_API_KEY=                # Для cloud whisper fallback
ADMIN_TG_ID=423051956
MAX_CONTEXT_MESSAGES=20
```

### 2. Зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. ffmpeg (для голосовых)

```bash
# Ubuntu/WSL
sudo apt update && sudo apt install ffmpeg
```

### 4. whisper.cpp с Vulkan (опционально, для локальной транскрибации на AMD RX 6900 XT)

Если `WHISPER_BACKEND=local`:
```bash
# Скачать whisper.cpp
mkdir -p ~/.local/share/whisper.cpp
# Собрать с Vulkan поддержкой (для AMD GPU)
# Инструкция: https://github.com/ggerganov/whisper.cpp#vulkan
```

Если Vulkan-версия не собрана — whisper автоматически переключится на OpenAI API.

## Запуск

### Обычный
```bash
cd /mnt/e/ClaudeCode/tg-claude
source .venv/bin/activate
python3 bot.py
```

### Фоновый
```bash
nohup python3 bot.py > bot.log 2>&1 &
echo $! > bot.pid
```

### Остановка
```bash
kill $(cat /mnt/e/ClaudeCode/tg-claude/bot.pid)
```

### Логи
```bash
tail -f /mnt/e/ClaudeCode/tg-claude/bot.log
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/clear` | Сбросить историю диалога |
| `/context` | Показать количество сообщений в памяти |
| `/help` | Справка |

## AI-провайдеры (fallback chain)

Приоритет:
1. **OpenRouter** — MiniMax M2.5 Free
2. **Groq** — Mistral (если OpenRouter rate-limited)
3. **Ollama** — локальный kimi-k2.5:cloud (если оба cloud недоступны)

При 429-ошибке от первого провайдера — автопереключение на следующий с задержкой 1 сек.

## Контекст и память

### Как работает
- **SQLite** — хранит историю чатов (`data/chat_memory.db`)
- **JSON** — синхронизирует контекст между сессиями (`tg-claude/.claude/context.json`)
- **Корневая JSON** — `E:\ClaudeCode\.claude\context.json` (общий контекст всех проектов)

### При запуске нового агента
1. Агент читает `cwd/.claude/context.json` (локальный)
2. Если нет — мержит с `E:\ClaudeCode\.claude\context.json` (корневой)
3. Если есть mempalace — мержит и с ним
4. Сохранение пишет в локальную папку **и** реплицирует в корневую

### Для агента (если спрашивают "помнишь меня?")
Вставь в промпт:
```python
from context_persistence import get_context_summary
print(get_context_summary())
```
Или в `README.md` указано, что агент должен при старте вызывать `load_context()`.

## Переключение провайдеров

В `.env`:
```
# Только OpenRouter
OPENROUTER_API_KEY=sk-...
GROQ_API_KEY=
OLLAMA_URL=

# Только Groq
OPENROUTER_API_KEY=
GROQ_API_KEY=gsk-...

# Только Ollama
OPENROUTER_API_KEY=
GROQ_API_KEY=
OLLAMA_URL=http://localhost:11434
```

## Переключение транскрибации

```
WHISPER_BACKEND=local    # whisper.cpp Vulkan (требует сборки)
WHISPER_BACKEND=openai   # OpenAI API (требует OPENAI_API_KEY)
```

## Claude Code: авто-разрешения

Файл `.claude/settings.json` настроен на автопропуск разрешений для:
- `pip install`, `python`, `python3`
- `mkdir`, `rm`, `cp`, `mv`, `touch`, `echo`
- `ffmpeg`, `git`, `apt`, `wget`, `curl`
- `ollama`, `whisper`

Агент не будет спрашивать "можно ли выполнить команду" — всё пропускается автоматически.

## Примечания

- **Telegram Bot Token** нужно получить у @BotFather и вписать в `.env`
- **OpenRouter** — MiniMax M2.5 Free имеет rate limits. При превышении — fallback на Groq.
- **AMD RX 6900 XT** — whisper.cpp с Vulkan быстрее CPU, но требует сборки из исходников.
- Если whisper.cpp не найден — автоматически используется OpenAI API (если ключ задан).
- Контекст агента (`context_persistence`) работает независимо от Telegram-бота — его можно импортировать в любой Python-скрипт.
