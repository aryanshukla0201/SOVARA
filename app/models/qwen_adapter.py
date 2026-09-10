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
                or "Answer directly. "
                "Return only the final answer. "
                "Do not reveal reasoning."
            ),
            "stream": False,
            "options": {
                "num_predict": 2048,
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 20,
                "repeat_penalty": 1.1,
            },
        }

        if options:
            payload["options"].update(options)

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

            response_text = data.get("response", "").strip()

            # Remove explicit thinking tags if the model emits them.
            response_text = re.sub(
                r"<think>.*?</think>",
                "",
                response_text,
                flags=re.DOTALL,
            ).strip()

            return response_text

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Ollama request failed for model "
                f"'{self.model_name}': {exc}"
            ) from exc

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **options: Any,
    ) -> str:
        return self._call_ollama(
            prompt,
            system_prompt=system_prompt,
            **options,
        )

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **options: Any,
    ) -> dict[str, Any]:

        structured_prompt = f"""
{prompt}

Return ONLY valid JSON.
Do not include explanations.
Do not include Markdown.
Do not include reasoning.
Do not include <think> tags.
"""

        raw = self._call_ollama(
            structured_prompt,
            system_prompt=system_prompt,
            **options,
        )

        raw = re.sub(
            r"<think>.*?</think>",
            "",
            raw,
            flags=re.DOTALL,
        ).strip()

        try:
            return json.loads(raw)

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                raw,
                flags=re.DOTALL,
            )

            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

            raise RuntimeError(
                "Qwen returned invalid structured JSON."
            )

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "QwenAdapter does not currently support direct image analysis."
        )