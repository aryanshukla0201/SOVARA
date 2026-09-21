from __future__ import annotations

from dataclasses import asdict, dataclass, field
from threading import Lock
from time import monotonic
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class RunTraceEvent:
    sequence: int
    trace_id: str
    task_id: str
    event_type: str
    timestamp_ms: float
    step_id: str | None = None
    tool_name: str | None = None
    status: str | None = None
    duration_ms: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentRunTrace:
    trace_id: str
    task_id: str
    plan_id: str | None
    started_at_ms: float
    events: list[RunTraceEvent] = field(default_factory=list)
    completed_at_ms: float | None = None
    status: str = "running"


class RunTrace:
    """
    In-memory ordered execution trace.

    This is observational only. It does not execute tools, alter policy,
    replace durable state, or change the execution path.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, AgentRunTrace] = {}
        self._sequences: dict[str, int] = {}

    def start_run(
        self,
        task_id: str,
        plan_id: str | None = None,
    ) -> str:
        if not task_id.strip():
            raise ValueError("task_id must not be empty")

        trace_id = uuid4().hex
        now = monotonic() * 1000

        with self._lock:
            self._runs[trace_id] = AgentRunTrace(
                trace_id=trace_id,
                task_id=task_id,
                plan_id=plan_id,
                started_at_ms=now,
            )
            self._sequences[trace_id] = 0
            self._append_locked(
                trace_id,
                "run_started",
                metadata={"plan_id": plan_id},
            )

        return trace_id

    def record_step_started(
        self,
        trace_id: str,
        step_id: str,
        tool_name: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record(
            trace_id,
            "step_started",
            step_id=step_id,
            tool_name=tool_name,
            status="running",
            metadata=metadata,
        )

    def record_step_completed(
        self,
        trace_id: str,
        step_id: str,
        tool_name: str,
        *,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record(
            trace_id,
            "step_completed",
            step_id=step_id,
            tool_name=tool_name,
            status="completed",
            duration_ms=duration_ms,
            metadata=metadata,
        )

    def record_step_failed(
        self,
        trace_id: str,
        step_id: str,
        tool_name: str,
        *,
        error: str,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record(
            trace_id,
            "step_failed",
            step_id=step_id,
            tool_name=tool_name,
            status="failed",
            duration_ms=duration_ms,
            error=error,
            metadata=metadata,
        )

    def record_step_skipped(
        self,
        trace_id: str,
        step_id: str,
        tool_name: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record(
            trace_id,
            "step_skipped",
            step_id=step_id,
            tool_name=tool_name,
            status="skipped",
            metadata=metadata,
        )

    def finish_run(
        self,
        trace_id: str,
        status: str,
    ) -> None:
        with self._lock:
            run = self._require_run_locked(trace_id)

            completed_at = monotonic() * 1000
            run.completed_at_ms = completed_at
            run.status = status

            duration_ms = max(
                0.0,
                completed_at - run.started_at_ms,
            )

            self._append_locked(
                trace_id,
                "run_completed",
                status=status,
                duration_ms=duration_ms,
            )

    def get_run(self, trace_id: str) -> AgentRunTrace:
        with self._lock:
            return self._require_run_locked(trace_id)

    def get_events(self, trace_id: str) -> list[RunTraceEvent]:
        with self._lock:
            return list(self._require_run_locked(trace_id).events)

    def snapshot(self, trace_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(trace_id)

            return {
                "trace_id": run.trace_id,
                "task_id": run.task_id,
                "plan_id": run.plan_id,
                "started_at_ms": run.started_at_ms,
                "completed_at_ms": run.completed_at_ms,
                "status": run.status,
                "events": [
                    event.to_dict()
                    for event in run.events
                ],
            }

    def _record(
        self,
        trace_id: str,
        event_type: str,
        *,
        step_id: str | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._require_run_locked(trace_id)

            self._append_locked(
                trace_id,
                event_type,
                step_id=step_id,
                tool_name=tool_name,
                status=status,
                duration_ms=duration_ms,
                error=error,
                metadata=metadata,
            )

    def _append_locked(
        self,
        trace_id: str,
        event_type: str,
        *,
        step_id: str | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sequence = self._sequences[trace_id] + 1
        self._sequences[trace_id] = sequence

        run = self._runs[trace_id]

        run.events.append(
            RunTraceEvent(
                sequence=sequence,
                trace_id=trace_id,
                task_id=run.task_id,
                event_type=event_type,
                timestamp_ms=monotonic() * 1000,
                step_id=step_id,
                tool_name=tool_name,
                status=status,
                duration_ms=duration_ms,
                error=error,
                metadata=dict(metadata or {}),
            )
        )

    def _require_run_locked(self, trace_id: str) -> AgentRunTrace:
        run = self._runs.get(trace_id)

        if run is None:
            raise KeyError(f"Trace not found: {trace_id}")

        return run
