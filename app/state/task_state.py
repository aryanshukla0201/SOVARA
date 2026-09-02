from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class TaskState(BaseModel):
    model_config = ConfigDict(extra="allow")

    intent: str = "general_analysis"
    required_capabilities: list[str] = Field(default_factory=list)
    requires_vision: bool = False
    requires_rag: bool = False
    requires_code: bool = False
    requires_tools: bool = False
    requires_synthesis: bool = False
    recommended_model_capability: str = "reasoning"
    output_format: str = "report"
    deliverable: str = "report"
    task_type: str | None = None
    detected_input_types: list[str] = Field(default_factory=list)
    reasoning_constraints: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "TaskState":
        return cls(**payload)
