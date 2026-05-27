"""Multi-provider LLM client with automatic fallback.

Priority:
1. Groq (llama-3.3-70b-versatile)
2. OpenRouter (deepseek/deepseek-v4-flash:free)
3. Ollama (local kimi-k2.6:cloud)
"""
import time
from typing import List, Dict, Optional
import requests
import config

SYSTEM_PROMPT = """Ты — AI-ассистент, работающий через Telegram-бота.
Ты общаешься с пользователем голосом и текстом. Отвечай кратко, по делу, без лишней воды.
Если просишь выполнить команду в терминале — пиши её в виде кода (блок ```bash).
Пользователь может отправлять голосовые сообщения — ты получаешь их текстовую расшифровку.
"""


class MultiProviderClient:
    """Клиент LLM с авто-fallback при rate limit (429)."""

    def __init__(self):
        self.providers = self._init_providers()

    def _init_providers(self) -> List[Dict]:
        """Возвращает список активных провайдеров по приоритету."""
        providers = []

        # 1. Groq (primary — стабильный и быстрый)
        if config.GROQ_API_KEY:
            providers.append({
                "name": "groq",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": config.GROQ_API_KEY,
                "model": config.GROQ_MODEL,
                "headers": {
                    "Authorization": f"Bearer {config.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
            })

        # 2. OpenRouter (fallback — free модели часто 429)
        if config.OPENROUTER_API_KEY:
            providers.append({
                "name": "openrouter",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "key": config.OPENROUTER_API_KEY,
                "model": config.OPENROUTER_MODEL,
                "headers": {
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://t.me/RSLhelper_bot",
                    "X-Title": "tg-claude"
                }
            })

        # 3. Ollama (local fallback)
        if config.OLLAMA_URL:
            providers.append({
                "name": "ollama",
                "url": f"{config.OLLAMA_URL}/api/chat",
                "key": None,
                "model": config.OLLAMA_MODEL,
                "headers": {"Content-Type": "application/json"}
            })

        return providers

    def _call_openrouter(self, provider: Dict, messages: List[Dict], max_tokens: int = 4096) -> str:
        payload = {
            "model": provider["model"],
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        resp = requests.post(provider["url"], headers=provider["headers"], json=payload, timeout=60)
        data = resp.json()
        if resp.status_code == 429:
            raise RateLimitError(data.get("error", {}).get("message", "429"))
        if "error" in data:
            raise LLMError(f"OpenRouter error: {data['error']}")
        msg = data["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning") or "(пустой ответ)"

    def _call_groq(self, provider: Dict, messages: List[Dict], max_tokens: int = 4096) -> str:
        payload = {
            "model": provider["model"],
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        resp = requests.post(provider["url"], headers=provider["headers"], json=payload, timeout=60)
        data = resp.json()
        if resp.status_code == 429:
            raise RateLimitError("Groq 429")
        if "error" in data:
            raise LLMError(f"Groq error: {data['error']}")
        msg = data["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning") or "(пустой ответ)"

    def _call_ollama(self, provider: Dict, messages: List[Dict], max_tokens: int = 4096) -> str:
        """Ollama API format differs slightly."""
        payload = {
            "model": provider["model"],
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": max_tokens},
        }
        resp = requests.post(provider["url"], headers=provider["headers"], json=payload, timeout=120)
        data = resp.json()
        if resp.status_code != 200:
            raise LLMError(f"Ollama error: {data}")
        return data.get("message", {}).get("content", "(пустой ответ)")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 4096) -> str:
        """Отправить диалог с авто-fallback при 429."""
        last_error = None

        for provider in self.providers:
            try:
                if provider["name"] == "openrouter":
                    return self._call_openrouter(provider, messages, max_tokens)
                elif provider["name"] == "groq":
                    return self._call_groq(provider, messages, max_tokens)
                elif provider["name"] == "ollama":
                    return self._call_ollama(provider, messages, max_tokens)
            except RateLimitError as e:
                last_error = f"{provider['name']}: {e}"
                print(f"[LLM] {provider['name']} rate limited, trying next...")
                time.sleep(1)
                continue
            except Exception as e:
                last_error = f"{provider['name']}: {e}"
                print(f"[LLM] {provider['name']} failed: {e}, trying next...")
                time.sleep(0.5)
                continue

        raise LLMError(f"All providers failed. Last: {last_error}")

    def chat_with_history(
        self,
        history: List[Dict[str, str]],
        user_message: str,
        max_tokens: int = 4096,
    ) -> str:
        """Добавить сообщение пользователя к истории и получить ответ."""
        msgs = history.copy()
        msgs.append({"role": "user", "content": user_message})
        return self.chat(msgs, max_tokens=max_tokens)


class RateLimitError(Exception):
    pass


class LLMError(Exception):
    pass
