from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from app.state.models import AgentTaskState


class DurableStateStore:
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
                CREATE TABLE IF NOT EXISTS agent_task_state (
                    task_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save(
        self,
        state: AgentTaskState,
        expected_version: int | None = None,
    ) -> AgentTaskState:
        with self._lock:
            connection = self._connect()

            try:
                connection.execute("BEGIN IMMEDIATE")

                row = connection.execute(
                    """
                    SELECT version
                    FROM agent_task_state
                    WHERE task_id = ?
                    """,
                    (state.task_id,),
                ).fetchone()

                current_version = (
                    int(row["version"])
                    if row is not None
                    else None
                )

                if current_version is not None:
                    if (
                        expected_version is not None
                        and current_version != expected_version
                    ):
                        raise ValueError(
                            "State version conflict: "
                            f"expected {expected_version}, "
                            f"found {current_version}"
                        )

                    if state.version <= current_version:
                        raise ValueError(
                            "State version must increase monotonically."
                        )

                elif expected_version not in (None, 0):
                    raise ValueError(
                        "Cannot apply expected version to a new task."
                    )

                payload = json.dumps(
                    state.to_dict(),
                    sort_keys=True,
                    ensure_ascii=False,
                )

                connection.execute(
                    """
                    INSERT INTO agent_task_state
                    (
                        task_id,
                        version,
                        state_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        version = excluded.version,
                        state_json = excluded.state_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        state.task_id,
                        state.version,
                        payload,
                        state.created_at,
                        state.updated_at,
                    ),
                )

                connection.commit()
                return state

            except Exception:
                connection.rollback()
                raise

            finally:
                connection.close()

    def get(
        self,
        task_id: str,
    ) -> AgentTaskState | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT state_json
                    FROM agent_task_state
                    WHERE task_id = ?
                    """,
                    (task_id,),
                ).fetchone()

            if row is None:
                return None

            return AgentTaskState.from_dict(
                json.loads(row["state_json"])
            )

    def delete(self, task_id: str) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    DELETE FROM agent_task_state
                    WHERE task_id = ?
                    """,
                    (task_id,),
                )
                connection.commit()

    def exists(self, task_id: str) -> bool:
        return self.get(task_id) is not None
