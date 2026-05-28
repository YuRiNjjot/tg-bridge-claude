"""Конфигурация бота. Загружает переменные из .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_admin_raw = os.getenv("ADMIN_TG_ID", "0")
try:
    ADMIN_TG_ID = int(_admin_raw)
except ValueError:
    ADMIN_TG_ID = 0

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

# Transcription: local Vulkan Whisper (AMD GPU) or disabled
WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", "local")  # "local" or "disabled"

_BASE_DIR = Path(__file__).parent

def _resolve_path(path_str):
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.is_absolute():
        p = _BASE_DIR / p
    return str(p.resolve())

# Whisper local paths (relative to repo root)
WHISPER_WINDOWS_EXE = _resolve_path(os.getenv("WHISPER_WINDOWS_EXE", ""))
WHISPER_WINDOWS_MODEL = _resolve_path(os.getenv("WHISPER_WINDOWS_MODEL", ""))
WHISPER_WINDOWS_TEMP = _resolve_path(os.getenv("WHISPER_WINDOWS_TEMP", ".\\data\\temp"))

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
    """Проверяет обязательные переменные окружения."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}. See .env.example")
