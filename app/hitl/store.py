from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from app.hitl.models import ApprovalRequest, ApprovalStatus


class ApprovalStore:
    """Durable SQLite persistence for HITL approval requests."""

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
                CREATE TABLE IF NOT EXISTS hitl_approval_requests (
                    approval_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    requested_action TEXT NOT NULL,
                    requested_arguments_summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_hitl_approvals_task_status
                ON hitl_approval_requests(task_id, status)
                """
            )
            connection.commit()

    def save(self, request: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO hitl_approval_requests
                    (
                        approval_id,
                        task_id,
                        step_id,
                        tool_name,
                        reason,
                        risk_level,
                        requested_action,
                        requested_arguments_summary,
                        created_at,
                        expires_at,
                        status,
                        metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(approval_id) DO UPDATE SET
                        status = excluded.status,
                        metadata_json = excluded.metadata_json
                    """,
                    (
                        request.approval_id,
                        request.task_id,
                        request.step_id,
                        request.tool_name,
                        request.reason,
                        request.risk_level,
                        request.requested_action,
                        request.requested_arguments_summary,
                        request.created_at,
                        request.expires_at,
                        request.status.value,
                        json.dumps(
                            request.metadata,
                            sort_keys=True,
                            ensure_ascii=False,
                        ),
                    ),
                )
                connection.commit()

        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        approval_id,
                        task_id,
                        step_id,
                        tool_name,
                        reason,
                        risk_level,
                        requested_action,
                        requested_arguments_summary,
                        created_at,
                        expires_at,
                        status,
                        metadata_json
                    FROM hitl_approval_requests
                    WHERE approval_id = ?
                    """,
                    (approval_id,),
                ).fetchone()

        if row is None:
            return None

        return self._from_row(row)

    def list_pending(
        self,
        task_id: str | None = None,
    ) -> list[ApprovalRequest]:
        with self._lock:
            with self._connect() as connection:
                if task_id is None:
                    rows = connection.execute(
                        """
                        SELECT
                            approval_id,
                            task_id,
                            step_id,
                            tool_name,
                            reason,
                            risk_level,
                            requested_action,
                            requested_arguments_summary,
                            created_at,
                            expires_at,
                            status,
                            metadata_json
                        FROM hitl_approval_requests
                        WHERE status = ?
                        ORDER BY created_at ASC
                        """,
                        (ApprovalStatus.PENDING.value,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """
                        SELECT
                            approval_id,
                            task_id,
                            step_id,
                            tool_name,
                            reason,
                            risk_level,
                            requested_action,
                            requested_arguments_summary,
                            created_at,
                            expires_at,
                            status,
                            metadata_json
                        FROM hitl_approval_requests
                        WHERE status = ? AND task_id = ?
                        ORDER BY created_at ASC
                        """,
                        (
                            ApprovalStatus.PENDING.value,
                            task_id,
                        ),
                    ).fetchall()

        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=row["approval_id"],
            task_id=row["task_id"],
            step_id=row["step_id"],
            tool_name=row["tool_name"],
            reason=row["reason"],
            risk_level=row["risk_level"],
            requested_action=row["requested_action"],
            requested_arguments_summary=row[
                "requested_arguments_summary"
            ],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            status=ApprovalStatus(row["status"]),
            metadata=json.loads(row["metadata_json"]),
        )
