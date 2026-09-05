from __future__ import annotations

import base64
import os
from typing import Any

import requests

from app.services.execution_telemetry import ExecutionTelemetry


class VisionAnalyzer:
    def __init__(
        self,
        model_name: str = "gemma3:4b-it-qat",
        base_url: str = "http://localhost:11434",
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.telemetry = telemetry

    def analyze(
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

The confidence value should be an estimate between 0.0 and 1.0
representing how clearly the observation is supported by the image.

Return JSON only.
""".strip()

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        }

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

        result = response.json()

        raw_response = result.get("response", "").strip()

        if not raw_response:
            raise ValueError(
                "Vision model returned an empty response."
            )

        parsed = self._parse_response(raw_response)

        return {
            "image_id": os.path.basename(image_path),
            "model": self.model_name,
            "observations": parsed["observations"],
        }

    @staticmethod
    def _parse_response(raw_response: str) -> dict[str, Any]:
        import json

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
            confidence = observation.get("confidence")

            if not isinstance(description, str):
                continue

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