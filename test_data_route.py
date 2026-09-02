from pathlib import Path

from app.state.workflow_state import WorkflowState, UploadedFileRecord
from app.workflow.graph import WorkflowGraph


# Create a small test CSV
test_dir = Path("data/test")
test_dir.mkdir(parents=True, exist_ok=True)

csv_path = test_dir / "sample.csv"

csv_path.write_text(
    """month,revenue,cost
January,100,60
February,120,70
March,150,80
April,180,100
""",
    encoding="utf-8",
)


# Create workflow state
state = WorkflowState(
    request_id="test_data_route",
    user_query="Analyze the revenue trend",
    uploaded_files=[
        UploadedFileRecord(
            file_id="test_csv_001",
            original_name="sample.csv",
            storage_path=str(csv_path),
            file_type="csv",
        )
    ],
)


# Run only the data route
workflow = WorkflowGraph()

result_state = workflow._data_route(state)


print("\nDATA RESULTS:")
print(result_state.data_results)