from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    evidence_id: str
    source_file_id: str | None = None
    source_filename: str | None = None
    page_number: int | None = None
    chunk_id: str | None = None
    text: str = ""
    relevance_score: float = 0.0
    retrieval_method: str = "manual"


class ToolResult(BaseModel):
    tool_name: str
    capability: str
    result: dict
    metadata: dict = Field(default_factory=dict)
