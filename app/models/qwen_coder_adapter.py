from __future__ import annotations

from app.models.qwen_adapter import QwenAdapter


class QwenCoderAdapter(QwenAdapter):
    DEFAULT_MODEL = "qwen2.5-coder:7b-instruct"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str = "http://127.0.0.1:11434",
        telemetry=None,
    ):
        super().__init__(
            model_name=model_name or self.DEFAULT_MODEL,
            base_url=base_url,
            telemetry=telemetry,
        )