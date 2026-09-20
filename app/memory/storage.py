from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.memory.models import MemoryRecord


class MemoryStorage:
    def __init__(self, db_path: str | Path = "data/sovara.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    memory_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    source TEXT,
                    reference_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, memory: MemoryRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_records (
                    memory_id,
                    content,
                    memory_type,
                    metadata,
                    source,
                    reference_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.memory_id,
                    memory.content,
                    memory.memory_type,
                    json.dumps(memory.metadata),
                    memory.source,
                    memory.reference_id,
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                ),
            )
            conn.commit()

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM memory_records
                WHERE memory_id = ?
                """,
                (memory_id,),
            ).fetchone()

        if row is None:
            return None

        return self._to_record(row)

    def list(
        self,
        memory_type: str | None = None,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        query = """
            SELECT *
            FROM memory_records
        """
        params: list[object] = []

        if memory_type is not None:
            query += " WHERE memory_type = ?"
            params.append(memory_type)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._to_record(row) for row in rows]

    def delete(self, memory_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM memory_records
                WHERE memory_id = ?
                """,
                (memory_id,),
            )
            conn.commit()

        return cursor.rowcount > 0

    @staticmethod
    def _to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row["memory_id"],
            content=row["content"],
            memory_type=row["memory_type"],
            metadata=json.loads(row["metadata"]),
            source=row["source"],
            reference_id=row["reference_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
