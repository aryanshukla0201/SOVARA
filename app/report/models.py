from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    REQUESTED = "requested"
    PREPARING = "preparing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportBlock(BaseModel):
    block_id: str
    block_type: str
    content: dict[str, Any] = Field(default_factory=dict)


class ReportSection(BaseModel):
    section_id: str
    title: str
    blocks: list[ReportBlock] = Field(default_factory=list)


class ReportFinding(BaseModel):
    finding_id: str
    finding_type: str
    severity: str | None = None
    title: str
    body: str
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: str = "unresolved"


class EvidenceReference(BaseModel):
    evidence_id: str
    source_file_id: str | None = None
    source_filename: str | None = None
    document_id: str | None = None
    page_number: int | None = None
    citation_id: str | None = None


class VerificationSummary(BaseModel):
    status: str = "pending"
    results: list[dict[str, Any]] = Field(default_factory=list)


class ArtifactReference(BaseModel):
    artifact_id: str
    name: str | None = None
    artifact_type: str | None = None
    location: str | None = None


class Report(BaseModel):
    report_id: str
    task_id: str
    run_id: str | None = None
    project_id: str | None = None

    title: str
    subtitle: str | None = None

    status: ReportStatus = ReportStatus.REQUESTED
    version: int = 1

    summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    findings: list[ReportFinding] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification: VerificationSummary = Field(
        default_factory=VerificationSummary
    )
    artifacts: list[ArtifactReference] = Field(default_factory=list)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
