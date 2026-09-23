from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.state.models import TaskStatus
from app.state.semantic_stage import (
    SemanticStage,
    SemanticStageStatus,
    stage_label,
)


@dataclass(frozen=True)
class SemanticStageView:
    stage_id: str
    run_id: str
    stage_type: SemanticStage
    status: SemanticStageStatus
    display_label: str
    sequence: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] | None = None


def project_task_stage(
    *,
    task_id: str,
    task_status: TaskStatus,
    stage: SemanticStage | None = None,
    status: SemanticStageStatus | None = None,
    sequence: int = 1,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> SemanticStageView:
    """
    Project authoritative task state into a frontend-safe semantic stage.

    This function is observational only. It does not mutate durable state
    and does not introduce a second execution state machine.
    """
    if task_status == TaskStatus.CANCELLED:
        stage = SemanticStage.CANCELLED
        status = SemanticStageStatus.CANCELLED
    elif task_status == TaskStatus.FAILED:
        stage = SemanticStage.FAILED
        status = SemanticStageStatus.FAILED
    elif task_status == TaskStatus.COMPLETED:
        stage = SemanticStage.COMPLETED
        status = SemanticStageStatus.COMPLETED
    else:
        if stage is None:
            stage = SemanticStage.UNDERSTANDING

        if status is None:
            status = SemanticStageStatus.RUNNING

    return SemanticStageView(
        stage_id=f"{task_id}:{stage.value}:{sequence}",
        run_id=task_id,
        stage_type=stage,
        status=status,
        display_label=stage_label(stage),
        sequence=sequence,
        started_at=started_at,
        completed_at=completed_at,
        metadata=dict(metadata or {}),
    )
