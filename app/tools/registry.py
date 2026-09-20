from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass
class ToolSpec:
    tool_name: str
    capability: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_task_types: list[str] = field(default_factory=list)

    description: str = ""
    risk_level: str = "low"
    permissions: list[str] = field(default_factory=list)
    execution_method: str = "local"
    timeout_seconds: int = 30
    enabled: bool = True


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, ToolSpec] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.register(
            ToolSpec(
                tool_name="DocumentRetriever",
                capability="document_analysis",
                description="Retrieve relevant evidence from indexed documents.",
                input_schema={"type": "pdf"},
                output_schema={"type": "evidence_list"},
                allowed_task_types=[
                    "equipment_analysis",
                    "document_analysis",
                ],
                risk_level="low",
                permissions=["local_documents"],
                execution_method="local",
                timeout_seconds=30,
            )
        )

        self.register(
            ToolSpec(
                tool_name="CSVAnalyzer",
                capability="data_analysis",
                description="Analyze structured CSV data.",
                input_schema={"type": "csv"},
                output_schema={"type": "analysis_result"},
                allowed_task_types=[
                    "equipment_analysis",
                    "data_analysis",
                ],
                risk_level="low",
                permissions=["local_files"],
                execution_method="local",
                timeout_seconds=30,
            )
        )

        self.register(
            ToolSpec(
                tool_name="VisionAnalyzer",
                capability="vision_analysis",
                description="Analyze visual content using the configured vision model.",
                input_schema={"type": "image"},
                output_schema={"type": "vision_observations"},
                allowed_task_types=[
                    "inspection",
                    "vision_analysis",
                ],
                risk_level="low",
                permissions=["local_images"],
                execution_method="local",
                timeout_seconds=120,
            )
        )

    def register(self, spec: ToolSpec) -> None:
        self._validate_spec(spec)

        if spec.tool_name in self.tools:
            raise ValueError(
                f"Tool already registered: {spec.tool_name}"
            )

        self.tools[spec.tool_name] = spec

    def get(self, tool_name: str) -> ToolSpec:
        try:
            return self.tools[tool_name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown tool: {tool_name}"
            ) from exc

    def list_tools(self) -> list[ToolSpec]:
        return list(self.tools.values())

    def get_tools_for_capability(
        self,
        capability: str,
    ) -> list[ToolSpec]:
        return [
            tool
            for tool in self.tools.values()
            if tool.capability == capability
        ]

    def get_allowed_tools(
        self,
        task_type: str,
    ) -> list[ToolSpec]:
        return [
            tool
            for tool in self.tools.values()
            if task_type in tool.allowed_task_types
        ]

    def get_available_tools(self) -> list[ToolSpec]:
        return [
            tool
            for tool in self.tools.values()
            if tool.enabled
        ]

    @staticmethod
    def _validate_spec(spec: ToolSpec) -> None:
        if not spec.tool_name.strip():
            raise ValueError("tool_name must not be empty")

        if not spec.capability.strip():
            raise ValueError("capability must not be empty")

        if spec.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        if spec.risk_level not in _VALID_RISK_LEVELS:
            raise ValueError(
                "risk_level must be one of: "
                + ", ".join(sorted(_VALID_RISK_LEVELS))
            )

        if not spec.execution_method.strip():
            raise ValueError(
                "execution_method must not be empty"
            )