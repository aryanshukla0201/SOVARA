from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict

from app.state.evidence import EvidenceRecord


class ResultState(BaseModel):
    model_config = ConfigDict(extra="allow")

    retrieved_evidence: list[EvidenceRecord] = Field(default_factory=list)
    document_results: list[dict] = Field(default_factory=list)
    data_results: list[dict] = Field(default_factory=list)
    vision_results: list[dict] = Field(default_factory=list)
    reasoning_results: list[dict] = Field(default_factory=list)
    aggregated_results: dict = Field(default_factory=dict)
    tools_used: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    direct_output: str = ""
    synthesis_required: bool = False
    synthesis_result: dict = Field(default_factory=dict)
    verification_results: list[dict] = Field(default_factory=list)
    verification_status: str = "pending"
    repair_attempts: int = 0
    final_answer: str = ""
    requested_deliverable: str | None = None
    generated_deliverables: list[str] = Field(default_factory=list)
