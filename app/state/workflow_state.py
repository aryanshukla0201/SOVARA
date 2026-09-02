from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.state.task_state import TaskState


class UploadedFileRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    file_id: str
    original_name: str
    storage_path: str
    file_type: str
    metadata: dict = Field(default_factory=dict)


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="allow")

    request_id: str
    user_query: str = ""
    input_metadata: dict = Field(default_factory=dict)
    input_types: dict[str, bool] | list[str] = Field(default_factory=dict)
    uploaded_files: list[UploadedFileRecord] = Field(default_factory=list)
    task_state: TaskState | None = None
    selected_routes: list[str] = Field(default_factory=list)
    pending_routes: list[str] = Field(default_factory=list)
    completed_routes: list[str] = Field(default_factory=list)
    current_route: str = ""
    selected_models: list[str] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    retrieved_evidence: list[dict] = Field(default_factory=list)
    document_results: list[dict] = Field(default_factory=list)
    data_results: list[dict] = Field(default_factory=list)
    vision_results: list[dict] = Field(default_factory=list)
    reasoning_results: list[dict] = Field(default_factory=list)
    aggregated_results: dict = Field(default_factory=dict)
    synthesis_required: bool = False
    synthesis_result: dict = Field(default_factory=dict)
    verification_results: list[dict] = Field(default_factory=list)
    verification_status: str = "pending"
    repair_attempts: int = 0
    final_answer: str = ""
    requested_deliverable: str = "report"
    generated_deliverables: list[str] = Field(default_factory=list)
    execution_trace: list[dict] = Field(default_factory=list)
