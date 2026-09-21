from __future__ import annotations

import os
from typing import Any

from app.models.gateway import ModelGateway
from app.services.execution_telemetry import ExecutionTelemetry


class VisionAnalyzer:
    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        telemetry: ExecutionTelemetry | None = None,
        gateway: ModelGateway | None = None,
    ):
        self.telemetry = telemetry

        self.gateway = gateway or ModelGateway(
            telemetry=telemetry,
        )

        self.model_name = model_name
        self.base_url = base_url

    def analyze(
        self,
        image_path: str,
        task_context: str,
    ) -> dict[str, Any]:

        if not os.path.isfile(image_path):
            raise FileNotFoundError(
                f"Image file not found: {image_path}"
            )

        if self.model_name:
            adapter = self.gateway.resolve_model(
                self.model_name,
                telemetry=self.telemetry,
            )
        else:
            adapter = self.gateway.resolve(
                "vision",
                telemetry=self.telemetry,
            )

        result = adapter.analyze_image(
            image_path=image_path,
            task_context=task_context,
        )

        if not isinstance(result, dict):
            raise ValueError(
                "Vision adapter returned an invalid response."
            )

        return result
