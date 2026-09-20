from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from app.state.models import AgentTaskState, Checkpoint


class CheckpointStore:
    def __init__(
        self,
        database_path: str | Path = "data/sovara_state.db",
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_checkpoints (
                    task_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, checkpoint_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_checkpoints_task_version
                ON agent_checkpoints(task_id, version)
                """
            )
            connection.commit()

    def save(self, checkpoint: Checkpoint) -> Checkpoint:
        with self._lock:
            with self._connect() as connection:
                existing = connection.execute(
                    """
                    SELECT 1
                    FROM agent_checkpoints
                    WHERE task_id = ? AND checkpoint_id = ?
                    """,
                    (
                        checkpoint.task_id,
                        checkpoint.checkpoint_id,
                    ),
                ).fetchone()

                if existing is not None:
                    raise ValueError(
                        "Checkpoint already exists: "
                        f"{checkpoint.checkpoint_id}"
                    )

                payload = json.dumps(
                    checkpoint.state.to_dict(),
                    sort_keys=True,
                    ensure_ascii=False,
                )

                connection.execute(
                    """
                    INSERT INTO agent_checkpoints
                    (
                        task_id,
                        checkpoint_id,
                        version,
                        state_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        checkpoint.task_id,
                        checkpoint.checkpoint_id,
                        checkpoint.version,
                        payload,
                        checkpoint.created_at,
                    ),
                )
                connection.commit()

        return checkpoint

    def get(
        self,
        task_id: str,
        checkpoint_id: str,
    ) -> Checkpoint | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        task_id,
                        checkpoint_id,
                        version,
                        state_json,
                        created_at
                    FROM agent_checkpoints
                    WHERE task_id = ? AND checkpoint_id = ?
                    """,
                    (
                        task_id,
                        checkpoint_id,
                    ),
                ).fetchone()

        if row is None:
            return None

        return Checkpoint(
            task_id=row["task_id"],
            checkpoint_id=row["checkpoint_id"],
            version=row["version"],
            state=AgentTaskState.from_dict(
                json.loads(row["state_json"])
            ),
            created_at=row["created_at"],
        )

    def latest(
        self,
        task_id: str,
    ) -> Checkpoint | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        task_id,
                        checkpoint_id,
                        version,
                        state_json,
                        created_at
                    FROM agent_checkpoints
                    WHERE task_id = ?
                    ORDER BY version DESC, created_at DESC
                    LIMIT 1
                    """,
                    (task_id,),
                ).fetchone()

        if row is None:
            return None

        return Checkpoint(
            task_id=row["task_id"],
            checkpoint_id=row["checkpoint_id"],
            version=row["version"],
            state=AgentTaskState.from_dict(
                json.loads(row["state_json"])
            ),
            created_at=row["created_at"],
        )

    def list_for_task(
        self,
        task_id: str,
    ) -> list[Checkpoint]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        task_id,
                        checkpoint_id,
                        version,
                        state_json,
                        created_at
                    FROM agent_checkpoints
                    WHERE task_id = ?
                    ORDER BY version ASC, created_at ASC
                    """,
                    (task_id,),
                ).fetchall()

        return [
            Checkpoint(
                task_id=row["task_id"],
                checkpoint_id=row["checkpoint_id"],
                version=row["version"],
                state=AgentTaskState.from_dict(
                    json.loads(row["state_json"])
                ),
                created_at=row["created_at"],
            )
            for row in rows
        ]
