"""Конфигурация бота. Загружает переменные из .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))

# AI Providers (fallback chain)
# Primary: OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-4b-it:free")

# Fallback 1: Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "mistral-saba-24b")

# Fallback 2: Ollama (local)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "kimi-k2.5:cloud")

# Transcription: OpenAI (cloud fallback) or local Vulkan Whisper
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", "local")  # "local", "openai", or "disabled"

# Whisper local paths (for GPU AMD via Vulkan + Windows exe)
WHISPER_WINDOWS_EXE = os.getenv("WHISPER_WINDOWS_EXE", "")
WHISPER_WINDOWS_MODEL = os.getenv("WHISPER_WINDOWS_MODEL", "")
WHISPER_WINDOWS_TEMP = os.getenv("WHISPER_WINDOWS_TEMP", "D:\\tmp\\tg-claude")

# Whisper Linux paths (for NVIDIA GPU or CPU)
WHISPER_LINUX_EXE = os.getenv("WHISPER_LINUX_EXE", "")
WHISPER_LINUX_MODEL = os.getenv("WHISPER_LINUX_MODEL", "")

# Vision: Ollama (local) or cloud APIs
VISION_BACKEND = os.getenv("VISION_BACKEND", "ollama")  # "ollama", "anthropic", "openai", or "disabled"
VISION_OLLAMA_MODEL = os.getenv("VISION_OLLAMA_MODEL", "llava")

# Anthropic API Key (for Claude Vision)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Context
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "chat_memory.db"
VOICE_DIR = DATA_DIR / "voice"
VOICE_DIR.mkdir(exist_ok=True)

# Claude Code integration
CLAUDE_MEMORY_FILE = Path(__file__).parent / ".claude" / "memory.json"
ROOT_MEMORY_FILE = Path("/mnt/e/ClaudeCode") / ".claude" / "memory.json"


def check_config():
    """Проверяет, что хотя бы один AI-провайдер задан."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not (OPENROUTER_API_KEY or GROQ_API_KEY or OLLAMA_URL):
        missing.append("OPENROUTER_API_KEY or GROQ_API_KEY or OLLAMA_URL")
    if not OPENAI_API_KEY and WHISPER_BACKEND == "openai":
        missing.append("OPENAI_API_KEY (for cloud whisper fallback)")
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}. See .env.example")
