from app.state.workflow_state import WorkflowState, UploadedFileRecord
from app.workflow.graph import WorkflowGraph


state = WorkflowState(
    request_id="test_pdf_graph_001",
    user_query="Analyze this document and summarize the important information.",
    uploaded_files=[
        UploadedFileRecord(
            file_id="test_pdf_001",
            original_name="Gaurav's_resume_AI_ML_research.pdf",
            storage_path="data\Gaurav's_resume_AI_ML_research.pdf",
            file_type="pdf",
        )
    ],
)

workflow = WorkflowGraph().build()

result = workflow.invoke(state)

print("\n========== INPUT TYPES ==========")
print(result["input_types"])

print("\n========== TASK STATE ==========")
print(result["task_state"])

print("\n========== SELECTED ROUTES ==========")
print(result["selected_routes"])

print("\n========== PENDING ROUTES ==========")
print(result["pending_routes"])

print("\n========== COMPLETED ROUTES ==========")
print(result["completed_routes"])

print("\n========== DOCUMENT RESULTS ==========")
print(result["document_results"])

print("\n========== RETRIEVED EVIDENCE ==========")
print(result["retrieved_evidence"])

print("\n========== REASONING RESULTS ==========")
print(result["reasoning_results"])

print("\n========== SYNTHESIS REQUIRED ==========")
print(result["synthesis_required"])

print("\n========== VERIFICATION STATUS ==========")
print(result["verification_status"])

print("\n========== FINAL ANSWER ==========")
print(result["final_answer"])

print("\n========== GENERATED DELIVERABLES ==========")
print(result["generated_deliverables"])