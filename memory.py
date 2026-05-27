"""SQLite-хранилище истории сообщений."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import config


class ChatMemory:
    """Хранит контекст диалога в SQLite."""

    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat ON messages(chat_id, timestamp)
            """)
            conn.commit()

    def add(self, chat_id: int, role: str, content: str):
        """Добавить сообщение в историю."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
                (chat_id, role, content),
            )
            conn.commit()

    def get_history(self, chat_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Получить последние N сообщений для чата."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()
        # Возвращаем в хронологическом порядке
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def clear(self, chat_id: int):
        """Очистить историю чата."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            conn.commit()
