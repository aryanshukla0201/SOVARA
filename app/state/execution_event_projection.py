from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.run_trace import RunTraceEvent
from app.state.semantic_stage import SemanticStage


@dataclass(frozen=True)
class UserSafeExecutionEvent:
    event_id: str
    run_id: str
    type: str
    stage: SemanticStage | None
    status: str | None
    sequence: int
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


def project_run_trace_events(
    events: list[RunTraceEvent],
) -> list[UserSafeExecutionEvent]:
    """
    Project RunTrace events into a frontend-safe event contract.

    RunTrace remains the execution-tracing authority. This projection is
    observational and does not mutate or replace the execution trace.
    """
    projected: list[UserSafeExecutionEvent] = []

    for event in events:
        metadata = dict(event.metadata)

        projected.append(
            UserSafeExecutionEvent(
                event_id=f"{event.trace_id}:{event.sequence}",
                run_id=event.task_id,
                type=event.event_type,
                stage=None,
                status=event.status,
                sequence=event.sequence,
                timestamp=event.timestamp_ms,
                metadata=metadata,
            )
        )

    return projected
