from __future__ import annotations

from typing import Any

from app.report.composer import ReportComposer
from app.report.models import Report
from app.report.store import ReportStore
from app.state.manager import AgentStateManager
from app.state.models import TaskStatus


class ReportService:
    """Coordinates report generation from an existing durable task result."""

    def __init__(
        self,
        state_manager: AgentStateManager | None = None,
        composer: ReportComposer | None = None,
        store: ReportStore | None = None,
    ) -> None:
        self.state_manager = state_manager or AgentStateManager()
        self.composer = composer or ReportComposer()
        self.store = store or ReportStore()

    def create_report(
        self,
        *,
        task_id: str,
        title: str | None = None,
        subtitle: str | None = None,
    ) -> Report:
        task = self.state_manager.require_task(task_id)

        if task.status != TaskStatus.COMPLETED:
            raise ValueError(
                f"Report generation requires a completed task; "
                f"task status is '{task.status.value}'."
            )

        result_payload = task.metadata.get("result")

        if not isinstance(result_payload, dict):
            raise ValueError("Completed task result is not available.")

        result = self._normalize_result(result_payload)

        existing_reports = self.store.list_for_task(task_id, limit=1)

        if existing_reports:
            existing = existing_reports[0]

            if title is None and subtitle is None:
                return existing

        report = self.composer.compose(
            task_id=task.task_id,
            run_id=task.metadata.get("run_id"),
            project_id=task.metadata.get("project_id"),
            result=result,
            title=title,
            subtitle=subtitle,
        )

        self.store.save(report)
        return report

    def get_report(self, report_id: str) -> Report | None:
        return self.store.get(report_id)

    def list_reports(
        self,
        *,
        task_id: str,
        limit: int = 50,
    ) -> list[Report]:
        self.state_manager.require_task(task_id)
        return self.store.list_for_task(task_id, limit=limit)

    @staticmethod
    def _normalize_result(payload: dict[str, Any]) -> Any:
        from app.state.result_state import ResultState

        return ResultState(
            final_answer=str(payload.get("final_answer") or ""),
            direct_output=str(payload.get("final_answer") or ""),
            retrieved_evidence=payload.get("evidence", []),
            verification_status=str(
                payload.get("verification_status") or "pending"
            ),
            verification_results=list(
                payload.get("verification_results") or []
            ),
            generated_deliverables=list(
                payload.get("generated_deliverables") or []
            ),
        )