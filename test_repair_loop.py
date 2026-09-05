from app.state.workflow_state import WorkflowState
from app.workflow.graph import WorkflowGraph

workflow_builder = WorkflowGraph()

# Force the final-answer node to produce a deliberately wrong answer.
# This lets us test whether the REAL verifier catches it and
# whether the REAL repair node fixes it.
workflow_builder._final_answer = lambda state: state.model_copy(
    update={
        "final_answer": (
            f"Revenue increased from 100 to 190, "
            f"representing a 90% increase "
            f"[{state.data_results[0]['evidence_id']}]"
        )
    }
)

workflow = workflow_builder.build()

state = WorkflowState(
    request_id="repair_loop_test",
    user_query="Analyze the revenue trend.",
    input_types={"csv": True},
    requested_deliverable="report",
)

state.uploaded_files = [
    {
        "file_id": "test_file",
        "original_name": "sample.csv",
        "storage_path": "data/test/sample.csv",
        "file_type": "csv",
    }
]

result = workflow.invoke(state)

print("\n========== REPAIR LOOP TEST ==========")
print("FINAL ANSWER:")
print(result["final_answer"])

print("\nVERIFICATION STATUS:")
print(result["verification_status"])

print("\nREPAIR ATTEMPTS:")
print(result["repair_attempts"])

print("\nEXECUTION TRACE:")
for step in result["execution_trace"]:
    print(" ->", step["node_name"])

print("======================================")
