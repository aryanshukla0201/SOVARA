from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from app.report.models import Report


class ReportStore:
    """Durable persistence for optional task reports."""

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
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reports_task_id
                ON reports(task_id)
                """
            )
            connection.commit()

    def save(self, report: Report) -> Report:
        payload = json.dumps(
            report.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
        )

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO reports (
                        report_id,
                        task_id,
                        version,
                        report_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_id) DO UPDATE SET
                        version = excluded.version,
                        report_json = excluded.report_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        report.report_id,
                        report.task_id,
                        report.version,
                        payload,
                        report.created_at.isoformat(),
                        report.updated_at.isoformat(),
                    ),
                )
                connection.commit()

        return report

    def get(self, report_id: str) -> Report | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT report_json
                    FROM reports
                    WHERE report_id = ?
                    """,
                    (report_id,),
                ).fetchone()

        if row is None:
            return None

        return Report.model_validate(
            json.loads(row["report_json"])
        )

    def list_for_task(
        self,
        task_id: str,
        limit: int = 50,
    ) -> list[Report]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT report_json
                    FROM reports
                    WHERE task_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (task_id, limit),
                ).fetchall()

        return [
            Report.model_validate(
                json.loads(row["report_json"])
            )
            for row in rows
        ]
