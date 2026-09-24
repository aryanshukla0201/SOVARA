from app.state.semantic_stage import (
    SemanticStage,
    SemanticStageStatus,
    stage_label,
)


def test_semantic_stage_values_are_frontend_safe():
    assert SemanticStage.UNDERSTANDING.value == "understanding"
    assert SemanticStage.PLANNING.value == "planning"
    assert SemanticStage.RETRIEVING.value == "retrieving"
    assert SemanticStage.ANALYZING.value == "analyzing"
    assert SemanticStage.GENERATING.value == "generating"
    assert SemanticStage.VERIFYING.value == "verifying"
    assert SemanticStage.WAITING_FOR_APPROVAL.value == "waiting_for_approval"
    assert SemanticStage.COMPLETED.value == "completed"
    assert SemanticStage.FAILED.value == "failed"
    assert SemanticStage.CANCELLED.value == "cancelled"


def test_semantic_stage_status_values_are_stable():
    assert [status.value for status in SemanticStageStatus] == [
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]


def test_semantic_stage_labels_are_deterministic():
    assert stage_label(SemanticStage.UNDERSTANDING) == "Understanding request"
    assert stage_label(SemanticStage.VERIFYING) == "Verifying result"
    assert stage_label(SemanticStage.CANCELLED) == "Cancelled"
