from __future__ import annotations

from app.services.execution_telemetry import ExecutionTelemetry
from app.tools.vision.image_analyzer import VisionAnalyzer


class VisionNode:
    def __init__(
        self,
        analyzer=None,
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.analyzer = analyzer or VisionAnalyzer(
            telemetry=telemetry
        )

    def run(
        self,
        image_path: str,
        task_context: str,
    ) -> dict:
        return self.analyzer.analyze(
            image_path,
            task_context,
        )