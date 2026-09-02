from app.state.workflow_state import UploadedFileRecord, WorkflowState
from app.workflow.graph import WorkflowGraph


csv_path = "data/sample.csv"


state = WorkflowState(
    request_id="test_full_graph_001",
    user_query="Analyze the trend in the revenue data.",
    uploaded_files=[
        UploadedFileRecord(
            file_id="test_csv_001",
            original_name="sample.csv",
            storage_path="data/test/sample.csv",
            file_type="csv",
        )
    ],
)


workflow = WorkflowGraph().build()


result = workflow.invoke(state)

print("\n========== INPUT TYPES ==========")
print(result.get("input_types"))

print("\n========== TASK STATE ==========")
print(result.get("task_state"))

print("\n========== SELECTED ROUTES ==========")
print(result.get("selected_routes"))

print("\n========== PENDING ROUTES ==========")
print(result.get("pending_routes"))

print("\n========== COMPLETED ROUTES ==========")
print(result.get("completed_routes"))


print("\n========== FINAL WORKFLOW RESULT ==========\n")

print("INPUT TYPES:")
print(result.get("input_types"))

print("\nSELECTED ROUTES:")
print(result.get("selected_routes"))

print("\nCOMPLETED ROUTES:")
print(result.get("completed_routes"))

print("\nCURRENT ROUTE:")
print(result.get("current_route"))

print("\nDATA RESULTS:")
print(result.get("data_results"))

print("\nAGGREGATED RESULTS:")
print(result.get("aggregated_results"))

print("\nSYNTHESIS REQUIRED:")
print(result.get("synthesis_required"))

print("\nVERIFICATION STATUS:")
print(result.get("verification_status"))

print("\nFINAL ANSWER:")
print(result.get("final_answer"))

print("\nGENERATED DELIVERABLES:")
print(result.get("generated_deliverables"))