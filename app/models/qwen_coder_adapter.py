from __future__ import annotations

from app.models.ollama_adapter import OllamaAdapter


class QwenCoderAdapter(OllamaAdapter):
    name = "qwen2.5-coder"

    DEFAULT_MODEL = "qwen2.5-coder:7b-instruct"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        telemetry=None,
    ):
        super().__init__(
            model_name=model_name or self.DEFAULT_MODEL,
            base_url=base_url,
            telemetry=telemetry,
        )