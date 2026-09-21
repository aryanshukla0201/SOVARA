from __future__ import annotations

import base64
import json
import os
from typing import Any, Callable

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.governance.budget import ResourceBudgetGovernor
from app.services.execution_telemetry import ExecutionTelemetry


class GemmaAdapter(BaseModelAdapter):
    name = "gemma3"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        telemetry: ExecutionTelemetry | None = None,
        performance_callback: Callable[..., None] | None = None,
        budget_governor: ResourceBudgetGovernor | None = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.gemma_model
        self.base_url = (
            base_url or settings.ollama_base_url
        ).rstrip("/")
        self.telemetry = telemetry
        self.performance_callback = performance_callback
        self.budget_governor = budget_governor

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        import time

        start_time = time.perf_counter()

        if self.budget_governor is not None:
            self.budget_governor.reserve_llm_call()

            requested_tokens = int(kwargs.get("num_predict", 2048))
            remaining = self.budget_governor.remaining("generated_tokens")

            if (
                remaining is not None
                and requested_tokens > remaining
            ):
                self.budget_governor.release("llm_calls")
                from app.governance.budget import BudgetExceededError

                raise BudgetExceededError(
                    "generated_tokens",
                    self.budget_governor.budget.max_generated_tokens,
                    self.budget_governor.usage.generated_tokens,
                    requested_tokens,
                )

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "system": system_prompt or "You are a vision assistant.",
                    "stream": False,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            result = data.get("response", "")

            duration_ms = (time.perf_counter() - start_time) * 1000

            eval_duration_ns = data.get("eval_duration", 0) or 0
            eval_count = data.get("eval_count", 0) or 0

            if self.budget_governor is not None:
                self.budget_governor.reserve_generated_tokens(
                    eval_count
                )

            generation_tokens_per_second = None

            if eval_duration_ns > 0 and eval_count > 0:
                generation_tokens_per_second = (
                    eval_count
                    / (eval_duration_ns / 1_000_000_000)
                )

            if self.performance_callback:
                self.performance_callback(
                    model_name=self.model_name,
                    generation_tokens_per_second=generation_tokens_per_second,
                    load_ms=(
                        (data.get("load_duration", 0) or 0)
                        / 1_000_000
                    ),
                )

            if self.telemetry:
                self.telemetry.record_llm_call(
                    model_name=self.model_name,
                    local=True,
                    duration_ms=duration_ms,
                    success=True,
                    input_chars=len(prompt),
                    output_chars=len(result),
                    ollama_total_duration_ms=(
                        (data.get("total_duration", 0) or 0)
                        / 1_000_000
                    ),
                    ollama_load_duration_ms=(
                        (data.get("load_duration", 0) or 0)
                        / 1_000_000
                    ),
                    ollama_prompt_eval_duration_ms=(
                        (data.get("prompt_eval_duration", 0) or 0)
                        / 1_000_000
                    ),
                    ollama_eval_duration_ms=(
                        (data.get("eval_duration", 0) or 0)
                        / 1_000_000
                    ),
                    ollama_prompt_eval_count=data.get(
                        "prompt_eval_count",
                        0,
                    ),
                    ollama_eval_count=eval_count,
                    ollama_generation_tokens_per_second=(
                        generation_tokens_per_second
                    ),
                )

            return result

        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000

            if self.telemetry:
                self.telemetry.record_llm_call(
                    model_name=self.model_name,
                    local=True,
                    duration_ms=duration_ms,
                    success=False,
                    input_chars=len(prompt),
                    output_chars=0,
                )

            return "Offline vision fallback response."

    def generate_structured(
        self,
        prompt: str,
        schema: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raw = self.generate(
            prompt,
            system_prompt=system_prompt,
        )

        try:
            return json.loads(raw)
        except Exception:
            return {
                "observations": [
                    {
                        "description": "Vision fallback",
                        "confidence": 0.5,
                    }
                ]
            }

    def analyze_image(
        self,
        image_path: str,
        task_context: str,
    ) -> dict[str, Any]:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(
                f"Image file not found: {image_path}"
            )

        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        prompt = f"""
You are the visual analysis component of SOVARA,
an evidence-driven multimodal analysis system.

Analyze the provided image specifically in the context of:

{task_context}

Identify only observations that are visually supported by the image.

Focus on:
- important objects or entities
- visible text
- diagrams, charts, or visual structures
- relationships between visible elements
- relevant visual patterns
- details that may help answer the user's task

Do not invent information that cannot be supported by the image.

Return your analysis as a JSON object with this structure:

{{
    "observations": [
        {{
            "description": "clear visual observation",
            "confidence": 0.0
        }}
    ]
}}

The confidence value should be an estimate between 0.0 and 1.0.

Return JSON only.
""".strip()

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()
        raw_response = data.get("response", "").strip()

        if not raw_response:
            raise ValueError(
                "Vision model returned an empty response."
            )

        parsed = self._parse_vision_response(raw_response)

        return {
            "image_id": os.path.basename(image_path),
            "model": self.model_name,
            "observations": parsed["observations"],
        }

    @staticmethod
    def _parse_vision_response(
        raw_response: str,
    ) -> dict[str, Any]:
        cleaned = raw_response.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Vision model did not return valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Vision model response must be a JSON object."
            )

        observations = parsed.get("observations")

        if not isinstance(observations, list):
            raise ValueError(
                "Vision model response is missing "
                "a valid observations list."
            )

        normalized_observations = []

        for observation in observations:
            if not isinstance(observation, dict):
                continue

            description = observation.get("description")

            if not isinstance(description, str):
                continue

            confidence = observation.get("confidence")

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None

            if confidence is not None:
                confidence = max(0.0, min(1.0, confidence))

            normalized_observations.append(
                {
                    "description": description,
                    "confidence": confidence,
                }
            )

        return {
            "observations": normalized_observations
        }
