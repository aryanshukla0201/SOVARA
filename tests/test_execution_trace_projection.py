from app.state.semantic_stage import SemanticStage, SemanticStageStatus
from app.state.execution_trace_projection import project_execution_trace


def test_execution_trace_projects_to_safe_semantic_stages():
    trace = [
        {
            "node_name": "input_processor",
            "model_used": "internal-model",
            "tools_used": ["file_detection"],
            "success": True,
            "relevant_output_ids": ["input_1"],
        },
        {
            "node_name": "task_analyzer",
            "model_used": "internal-model",
            "tools_used": [],
            "success": True,
            "relevant_output_ids": [],
        },
        {
            "node_name": "vault_route",
            "model_used": "internal-model",
            "tools_used": ["KnowledgeVault"],
            "success": True,
            "relevant_output_ids": ["ev_1"],
        },
        {
            "node_name": "verifier",
            "model_used": "internal-model",
            "tools_used": [],
            "success": True,
            "relevant_output_ids": [],
        },
    ]

    stages = project_execution_trace(
        run_id="task-1",
        execution_trace=trace,
    )

    assert [stage.stage_type for stage in stages] == [
        SemanticStage.UNDERSTANDING,
        SemanticStage.PLANNING,
        SemanticStage.RETRIEVING,
        SemanticStage.VERIFYING,
    ]

    assert all(
        stage.status == SemanticStageStatus.COMPLETED
        for stage in stages
    )

    assert stages[0].run_id == "task-1"
    assert stages[0].stage_id == "task-1:understanding:1"


def test_unknown_internal_nodes_are_hidden():
    trace = [
        {
            "node_name": "input_processor",
            "success": True,
        },
        {
            "node_name": "_internal_helper",
            "model_used": "secret-model",
            "tools_used": ["internal_tool"],
            "success": True,
        },
        {
            "node_name": "verifier",
            "success": True,
        },
    ]

    stages = project_execution_trace(
        run_id="task-2",
        execution_trace=trace,
    )

    assert len(stages) == 2
    assert [
        stage.stage_type
        for stage in stages
    ] == [
        SemanticStage.UNDERSTANDING,
        SemanticStage.VERIFYING,
    ]


def test_failed_trace_event_projects_to_failed_stage():
    trace = [
        {
            "node_name": "verifier",
            "success": False,
        },
    ]

    stages = project_execution_trace(
        run_id="task-3",
        execution_trace=trace,
    )

    assert len(stages) == 1
    assert stages[0].stage_type == SemanticStage.VERIFYING
    assert stages[0].status == SemanticStageStatus.FAILED
