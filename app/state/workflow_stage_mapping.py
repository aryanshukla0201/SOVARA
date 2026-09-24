from __future__ import annotations

from app.state.semantic_stage import SemanticStage


WORKFLOW_STAGE_MAP: dict[str, SemanticStage] = {
    "input_processor": SemanticStage.UNDERSTANDING,
    "task_analyzer": SemanticStage.PLANNING,
    "policy_router": SemanticStage.PLANNING,
    "execution_dispatch": SemanticStage.PLANNING,
    "document_route": SemanticStage.RETRIEVING,
    "document_fact": SemanticStage.RETRIEVING,
    "vault_route": SemanticStage.RETRIEVING,
    "data_route": SemanticStage.RETRIEVING,
    "vision_route": SemanticStage.ANALYZING,
    "reasoning_route": SemanticStage.ANALYZING,
    "code_execution": SemanticStage.ANALYZING,
    "aggregate_results": SemanticStage.ANALYZING,
    "complexity_gate": SemanticStage.ANALYZING,
    "synthesis": SemanticStage.GENERATING,
    "final_answer": SemanticStage.GENERATING,
    "verifier": SemanticStage.VERIFYING,
    "deliverable": SemanticStage.GENERATING,
}


def semantic_stage_for_node(
    node_name: str,
) -> SemanticStage | None:
    """
    Map an internal workflow node to a frontend-safe semantic stage.

    Unmapped/internal nodes are intentionally hidden rather than exposed
    as implementation details.
    """
    return WORKFLOW_STAGE_MAP.get(node_name)
