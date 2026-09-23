from __future__ import annotations

from enum import Enum


class SemanticStage(str, Enum):
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VERIFYING = "verifying"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SemanticStageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


STAGE_LABELS: dict[SemanticStage, str] = {
    SemanticStage.UNDERSTANDING: "Understanding request",
    SemanticStage.PLANNING: "Planning",
    SemanticStage.RETRIEVING: "Retrieving information",
    SemanticStage.ANALYZING: "Analyzing",
    SemanticStage.GENERATING: "Generating result",
    SemanticStage.VERIFYING: "Verifying result",
    SemanticStage.WAITING_FOR_APPROVAL: "Waiting for approval",
    SemanticStage.COMPLETED: "Completed",
    SemanticStage.FAILED: "Failed",
    SemanticStage.CANCELLED: "Cancelled",
}


def stage_label(stage: SemanticStage) -> str:
    return STAGE_LABELS[stage]
