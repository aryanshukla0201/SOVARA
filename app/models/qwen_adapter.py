from __future__ import annotations

import json
import re
from typing import Any

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.services.execution_telemetry import ExecutionTelemetry


class QwenAdapter(BaseModelAdapter):

    name = "qwen3"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        telemetry: ExecutionTelemetry | None = None,
    ):
        settings = get_settings()

        self.model_name = model_name or settings.qwen_model
        self.base_url = base_url or settings.ollama_base_url
        self.telemetry = telemetry

    def _call_ollama(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **options: Any,
    ) -> str:

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": (
                system_prompt
                or "You are a careful reasoning and analysis engine."
            ),
            "stream": False,
        }

        if options:
            payload["options"] = options

        
        try:
            if self.telemetry is not None:
                self.telemetry.record_llm_call(
                    model_name=self.model_name,
                    local=self.base_url.startswith(
                        ("http://localhost", "http://127.0.0.1")
                    ),
                )
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            )

            response.raise_for_status()

            data = response.json()

            return data.get("response", "").strip()

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Ollama request failed for model '{self.model_name}': {exc}"
            ) from exc

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:

        return self._call_ollama(
            prompt,
            system_prompt,
            **kwargs,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:

        structured_prompt = f"""
Return ONLY valid JSON.

Do not include markdown.
Do not include explanations.
Do not include text before or after the JSON.

Expected schema:

{schema}

Task:

{prompt}
"""

        raw = self.generate(
            structured_prompt,
            system_prompt=(
                system_prompt
                or "You are a structured output engine."
            ),
            **kwargs,
        )

        try:
            return json.loads(raw)

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                raw,
                re.DOTALL,
            )

            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                f"Model returned invalid structured JSON: {raw[:500]}"
            )

    def analyze_image(
        self,
        image_path: str,
        task_context: str,
    ) -> dict[str, Any]:

        raise NotImplementedError(
            "QwenAdapter text model does not currently implement image analysis."
        )