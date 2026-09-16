from __future__ import annotations

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.models.gemma_adapter import GemmaAdapter
from app.models.ollama_adapter import OllamaAdapter
from app.models.qwen_coder_adapter import QwenCoderAdapter
from app.services.execution_telemetry import ExecutionTelemetry


class Phi4MiniAdapter(OllamaAdapter):
    name = "phi4-mini"

    DEFAULT_MODEL = "phi4-mini:latest"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        telemetry: ExecutionTelemetry | None = None,
    ):
        super().__init__(
            model_name=model_name or self.DEFAULT_MODEL,
            base_url=base_url,
            telemetry=telemetry,
        )


class ModelFactory:

    @staticmethod
    def create(
        model_type: str,
        telemetry: ExecutionTelemetry | None = None,
        **kwargs,
    ) -> BaseModelAdapter:

        settings = get_settings()

        if model_type == "reasoning":
            return Phi4MiniAdapter(
                model_name=(
                    kwargs.get("model_name")
                    or "phi4-mini:latest"
                ),
                base_url=(
                    kwargs.get("base_url")
                    or settings.ollama_base_url
                ),
                telemetry=telemetry,
            )

        if model_type == "qwen_coder":
            return QwenCoderAdapter(
                model_name=(
                    kwargs.get("model_name")
                    or "qwen2.5-coder:7b-instruct"
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