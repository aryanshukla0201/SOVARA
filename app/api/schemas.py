from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    user_query: str
    requested_deliverable: str | None = None


class AnalysisResponse(BaseModel):
    request_id: str
    status: str
    final_answer: str
    evidence: list[dict] = Field(default_factory=list)
    verification_status: str = "pending"
    traceability: list[dict] = Field(default_factory=list)
    generated_deliverables: list[str] = Field(default_factory=list)
