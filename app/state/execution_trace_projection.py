from __future__ import annotations

from typing import Any

from app.state.semantic_stage import (
    SemanticStage,
    SemanticStageStatus,
)
from app.state.semantic_stage_projection import SemanticStageView
from app.state.workflow_stage_mapping import semantic_stage_for_node


def project_execution_trace(
    *,
    run_id: str,
    execution_trace: list[dict[str, Any]],
) -> list[SemanticStageView]:
    """
    Convert the existing internal workflow trace into frontend-safe
    semantic stage views.

    Internal workflow details are intentionally not exposed.
    Unknown nodes are ignored.
    """
    stages: list[SemanticStageView] = []

    for sequence, event in enumerate(execution_trace, start=1):
        node_name = event.get("node_name", "")
        stage = semantic_stage_for_node(node_name)

        if stage is None:
            continue

        success = event.get("success", True)

        status = (
            SemanticStageStatus.COMPLETED
            if success
            else SemanticStageStatus.FAILED
        )

        stages.append(
            SemanticStageView(
                stage_id=f"{run_id}:{stage.value}:{sequence}",
                run_id=run_id,
                stage_type=stage,
                status=status,
                display_label={
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
                }[stage],
                sequence=sequence,
                metadata={},
            )
        )

    return stages
