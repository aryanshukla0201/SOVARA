from types import SimpleNamespace
from unittest.mock import patch

from app.state.workflow_state import UploadedFileRecord, WorkflowState
from app.workflow.graph import WorkflowGraph


def test_vision_route_uses_analyzer_model_name_for_trace():
    state = WorkflowState(
        request_id="req_test",
        user_query="Analyze this image.",
        uploaded_files=[
            UploadedFileRecord(
                file_id="file_test",
                original_name="test.png",
                storage_path="test.png",
                file_type="image",
            )
        ],
    )

    fake_result = {
        "model": "gemma3:4b-it-qat",
        "observations": [
            {
                "description": "A test image",
                "confidence": 0.9,
            }
        ],
    }

    vision_node = SimpleNamespace(
        analyzer=SimpleNamespace(
            model_name="gemma3:4b-it-qat"
        ),
        run=lambda image_path, task_context: fake_result,
    )

    graph = WorkflowGraph.__new__(WorkflowGraph)
    graph.telemetry = None

    with patch(
        "app.workflow.graph.VisionNode",
        return_value=vision_node,
    ), patch.object(
        graph,
        "_trace",
        side_effect=lambda state, **kwargs: state.execution_trace.append(kwargs),
    ):
        result = graph._vision_route(state)

    trace = result.execution_trace[-1]

    assert trace["node_name"] == "vision_route"
    assert trace["model_used"] == "gemma3:4b-it-qat"
    assert "file_test_ev_001" in trace["relevant_output_ids"]
