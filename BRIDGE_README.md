# Telegram Bridge для Claude Code

## Как работает

```
Telegram User --> Bridge Bot --> bridge_messages.jsonl
                                     |
                                     v
                               Claude Code (читает лог)
                                     |
                                     v
                          bridge_outbox.jsonl --> Telegram
```

## Компоненты

### bridge_bot.py
- Получает сообщения из Telegram (polling)
- Транскрибирует голосовые через whisper.cpp на AMD RX 6900 XT (Vulkan)
- Пишет все в `data/bridge_messages.jsonl`
- Читает ответы из `data/bridge_outbox.jsonl` и отправляет в Telegram
- Запущен в фоне, PID: `1853219`

### bridge_reader.py
- Helper для Claude Code
- `python bridge_reader.py` — показать новые сообщения
- `python bridge_reader.py --reply` — интерактивный режим ответов

## Файлы

| Файл | Назначение |
|------|-----------|
| `data/bridge_messages.jsonl` | Входящие сообщения от пользователя |
| `data/bridge_outbox.jsonl` | Исходящие ответы от Claude |
| `data/bridge.log` | Лог работы bridge_bot |
| `data/.bridge_state` | Последний обработанный update_id |

## Whisper GPU

- **Устройство**: AMD Radeon RX 6900 XT
- **Backend**: Vulkan (через Windows whisper-cli.exe)
- **Модель**: ggml-small.bin
- **Время транскрибации**: ~5-6 сек для 15-секундного аудио

## Как ответить из Claude Code

```python
import json
with open('data/bridge_outbox.jsonl', 'a') as f:
    f.write(json.dumps({
        'chat_id': 423051956,
        'text': 'Твой ответ',
        'reply_to': 123  # message_id для reply
    }, ensure_ascii=False) + '\n')
```

## Перезапуск

```bash
# Найти PID
ps aux | grep bridge_bot

# Убить и перезапустить
kill <PID>
PYTHONUNBUFFERED=1 python3 bridge_bot.py > data/bridge.log 2>&1 &
```
