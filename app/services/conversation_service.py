from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path


class ConversationService:
    def __init__(self):
        self.db_path = Path("data/sovara.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
                )
                """
            )

            conn.commit()

    def create_conversation(self) -> str:
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (conversation_id)
                VALUES (?)
                """,
                (conversation_id,),
            )
            conn.commit()

        return conversation_id

    def exists(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return row is not None

    def get_history(self, conversation_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [
            {
                "role": role,
                "content": content,
            }
            for role, content in rows
        ]

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        if not self.exists(conversation_id):
            raise ValueError(
                f"Conversation not found: {conversation_id}"
            )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_messages
                (conversation_id, role, content)
                VALUES (?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                ),
            )
            conn.commit()