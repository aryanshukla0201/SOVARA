from app.state.semantic_stage import SemanticStage
from app.state.workflow_stage_mapping import semantic_stage_for_node


def test_understanding_node_maps_to_understanding():
    assert (
        semantic_stage_for_node("input_processor")
        == SemanticStage.UNDERSTANDING
    )


def test_planning_nodes_map_to_planning():
    assert semantic_stage_for_node("task_analyzer") == SemanticStage.PLANNING
    assert semantic_stage_for_node("policy_router") == SemanticStage.PLANNING
    assert semantic_stage_for_node("execution_dispatch") == SemanticStage.PLANNING


def test_retrieval_nodes_map_to_retrieving():
    assert semantic_stage_for_node("document_route") == SemanticStage.RETRIEVING
    assert semantic_stage_for_node("vault_route") == SemanticStage.RETRIEVING
    assert semantic_stage_for_node("data_route") == SemanticStage.RETRIEVING


def test_analysis_nodes_map_to_analyzing():
    assert semantic_stage_for_node("vision_route") == SemanticStage.ANALYZING
    assert semantic_stage_for_node("reasoning_route") == SemanticStage.ANALYZING
    assert semantic_stage_for_node("code_execution") == SemanticStage.ANALYZING
    assert semantic_stage_for_node("aggregate_results") == SemanticStage.ANALYZING


def test_generation_and_verification_nodes_map_correctly():
    assert semantic_stage_for_node("synthesis") == SemanticStage.GENERATING
    assert semantic_stage_for_node("final_answer") == SemanticStage.GENERATING
    assert semantic_stage_for_node("deliverable") == SemanticStage.GENERATING
    assert semantic_stage_for_node("verifier") == SemanticStage.VERIFYING


def test_unknown_internal_node_is_not_exposed():
    assert semantic_stage_for_node("some_internal_helper") is None
