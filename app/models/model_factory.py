from __future__ import annotations

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.models.gemma_adapter import GemmaAdapter
from app.models.qwen_adapter import QwenAdapter
from app.services.execution_telemetry import ExecutionTelemetry


class ModelFactory:

    @staticmethod
    def create(
        model_type: str,
        telemetry: ExecutionTelemetry | None = None,
        **kwargs,
    ) -> BaseModelAdapter:

        settings = get_settings()

        if model_type == "qwen":
            return QwenAdapter(
                model_name=(
                    kwargs.get("model_name")
                    or settings.qwen_model
                ),
                base_url=(
                    kwargs.get("base_url")
                    or settings.ollama_base_url
                ),
                telemetry=telemetry,
            )

        if model_type == "gemma":
            return GemmaAdapter(
                model_name=(
                    kwargs.get("model_name")
                    or settings.gemma_model
                ),
                base_url=(
                    kwargs.get("base_url")
                    or settings.ollama_base_url
                ),
            )

        raise ValueError(
            f"Unsupported model type: {model_type}"
        )