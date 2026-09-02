from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSpec:
    tool_name: str
    capability: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_task_types: list[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, ToolSpec] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.register(
            ToolSpec(
                tool_name="DocumentRetriever",
                capability="document_analysis",
                input_schema={"type": "pdf"},
                output_schema={"type": "evidence_list"},
                allowed_task_types=["equipment_analysis", "document_analysis"],
            )
        )
        self.register(
            ToolSpec(
                tool_name="CSVAnalyzer",
                capability="data_analysis",
                input_schema={"type": "csv"},
                output_schema={"type": "analysis_result"},
                allowed_task_types=["equipment_analysis", "data_analysis"],
            )
        )
        self.register(
            ToolSpec(
                tool_name="VisionAnalyzer",
                capability="vision_analysis",
                input_schema={"type": "image"},
                output_schema={"type": "vision_observations"},
                allowed_task_types=["inspection", "vision_analysis"],
            )
        )

    def register(self, spec: ToolSpec) -> None:
        self.tools[spec.tool_name] = spec

    def get_tools_for_capability(self, capability: str) -> list[ToolSpec]:
        return [tool for tool in self.tools.values() if tool.capability == capability]

    def get_allowed_tools(self, task_type: str) -> list[ToolSpec]:
        return [tool for tool in self.tools.values() if task_type in tool.allowed_task_types]
