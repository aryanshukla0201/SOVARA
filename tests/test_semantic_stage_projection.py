from app.state.models import TaskStatus
from app.state.semantic_stage import SemanticStage, SemanticStageStatus
from app.state.semantic_stage_projection import project_task_stage


def test_completed_task_projects_to_completed_stage():
    view = project_task_stage(
        task_id="task-1",
        task_status=TaskStatus.COMPLETED,
        sequence=4,
    )

    assert view.run_id == "task-1"
    assert view.stage_type == SemanticStage.COMPLETED
    assert view.status == SemanticStageStatus.COMPLETED
    assert view.display_label == "Completed"
    assert view.sequence == 4
    assert view.stage_id == "task-1:completed:4"


def test_failed_task_projects_to_failed_stage():
    view = project_task_stage(
        task_id="task-2",
        task_status=TaskStatus.FAILED,
    )

    assert view.stage_type == SemanticStage.FAILED
    assert view.status == SemanticStageStatus.FAILED


def test_cancelled_task_projects_to_cancelled_stage():
    view = project_task_stage(
        task_id="task-3",
        task_status=TaskStatus.CANCELLED,
    )

    assert view.stage_type == SemanticStage.CANCELLED
    assert view.status == SemanticStageStatus.CANCELLED


def test_running_task_requires_no_new_persistent_state():
    view = project_task_stage(
        task_id="task-4",
        task_status=TaskStatus.RUNNING,
        stage=SemanticStage.RETRIEVING,
        sequence=2,
    )

    assert view.stage_type == SemanticStage.RETRIEVING
    assert view.status == SemanticStageStatus.RUNNING
    assert view.display_label == "Retrieving information"
    assert view.stage_id == "task-4:retrieving:2"


def test_explicit_stage_status_is_preserved():
    view = project_task_stage(
        task_id="task-5",
        task_status=TaskStatus.RUNNING,
        stage=SemanticStage.VERIFYING,
        status=SemanticStageStatus.COMPLETED,
        sequence=5,
    )

    assert view.stage_type == SemanticStage.VERIFYING
    assert view.status == SemanticStageStatus.COMPLETED


def test_metadata_and_timestamps_are_projection_only():
    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)
    completed = datetime.now(timezone.utc)

    view = project_task_stage(
        task_id="task-6",
        task_status=TaskStatus.RUNNING,
        stage=SemanticStage.GENERATING,
        sequence=3,
        started_at=started,
        completed_at=completed,
        metadata={"source": "workflow"},
    )

    assert view.started_at == started
    assert view.completed_at == completed
    assert view.metadata == {"source": "workflow"}
