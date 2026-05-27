#!/usr/bin/env python3
"""
tg-claude — Telegram-бот для общения с AI через OpenRouter/Groq/Ollama.
Принимает текст и голосовые, сохраняет контекст, отвечает с fallback-провайдерами.

Запуск:
    python bot.py
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from llm_client import MultiProviderClient
from memory import ChatMemory
from whisper_client import transcribe

# === Logging ===
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# === Init ===
config.check_config()
memory = ChatMemory()
llm = MultiProviderClient()


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — приветствие."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        "Привет! Я бот с AI.\n\n"
        "Отправь текст или голосовое — я отвечу.\n"
        "Используй /clear чтобы сбросить контекст.\n"
        "Используй /help для списка команд."
    )
    logger.info(f"User {chat_id} started bot")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help — список команд."""
    text = (
        "*Команды:*\n"
        "/start — начать\n"
        "/clear — сбросить историю диалога\n"
        "/context — сколько сообщений в памяти\n"
        "/help — эта справка\n\n"
        "*AI-провайдеры (авто-fallback):*\n"
        "1. OpenRouter (MiniMax M2.5)\n"
        "2. Groq (Mistral)\n"
        "3. Ollama (локальный)\n\n"
        "*Транскрибация:*\n"
        "Голосовые → whisper.cpp (Vulkan) → AI\n"
        "Если Vulkan недоступен — OpenAI fallback"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/clear — очистить историю чата."""
    chat_id = update.effective_chat.id
    memory.clear(chat_id)
    await update.message.reply_text("Контекст очищен. Начинаем с чистого листа.")
    logger.info(f"User {chat_id} cleared context")


async def context_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/context — показать количество сообщений в памяти."""
    chat_id = update.effective_chat.id
    history = memory.get_history(chat_id, limit=9999)
    user_msgs = sum(1 for m in history if m["role"] == "user")
    ai_msgs = sum(1 for m in history if m["role"] == "assistant")
    await update.message.reply_text(
        f"Сообщений в памяти: {len(history)}\n"
        f"  Пользователь: {user_msgs}\n"
        f"  AI: {ai_msgs}"
    )


async def _process_text(chat_id: int, user_text: str, reply_func):
    """Core: отправить текст в LLM и вернуть ответ."""
    if not user_text.strip():
        return

    logger.info(f"User {chat_id}: {user_text[:80]}")

    # Добавить сообщение пользователя в память
    memory.add(chat_id, "user", user_text)

    # Получить историю (без текущего сообщения — оно уже добавлено)
    history = memory.get_history(chat_id, limit=config.MAX_CONTEXT_MESSAGES)
    history_for_llm = [h for h in history if not (h["role"] == "user" and h["content"] == user_text)]

    # Запрос к LLM с fallback
    try:
        response = llm.chat_with_history(history_for_llm, user_text)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        await reply_func(f"Ошибка AI: {e}")
        return

    # Сохранить ответ
    memory.add(chat_id, "assistant", response)

    # Отправить ответ (если длинный — разбить)
    if len(response) <= 4096:
        await reply_func(response)
    else:
        for i in range(0, len(response), 4096):
            await reply_func(response[i:i + 4096])

    logger.info(f"AI to {chat_id}: {response[:80]}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового сообщения."""
    chat_id = update.effective_chat.id
    user_text = update.message.text or ""
    await _process_text(chat_id, user_text, update.message.reply_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосового: скачать → транскрибировать → отправить в LLM."""
    chat_id = update.effective_chat.id
    voice = update.message.voice

    if not voice:
        return

    await update.message.reply_text("Слушаю...")

    # Скачать файл
    voice_file = await voice.get_file()
    ogg_name = f"voice_{chat_id}_{voice.file_id}.ogg"
    ogg_path = config.VOICE_DIR / ogg_name
    await voice_file.download_to_drive(ogg_path)

    # Транскрибировать
    transcript = transcribe(ogg_path)

    # Удалить OGG
    ogg_path.unlink(missing_ok=True)

    if not transcript:
        await update.message.reply_text("Не удалось распознать голосовое. Попробуй ещё раз.")
        return

    # Показать распознанный текст
    await update.message.reply_text(f"🎤 _{transcript}_", parse_mode="Markdown")

    # Отправить в LLM как текстовое сообщение
    await _process_text(chat_id, transcript, update.message.reply_text)


async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок."""
    logger.error(f"Exception: {context.error}", exc_info=True)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Попробуй позже или напиши /clear."
        )


def main():
    logger.info("Starting tg-claude bot...")
    logger.info(f"Providers: {[p['name'] for p in llm.providers]}")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("context", context_cmd))

    # Голосовые
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Текст (всё остальное)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Ошибки
    app.add_error_handler(error_handler)

    logger.info("Bot polling started")
    app.run_polling()


if __name__ == "__main__":
    main()
