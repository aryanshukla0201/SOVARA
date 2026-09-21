from __future__ import annotations

import base64
import json
import os
from typing import Any

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter


class GemmaAdapter(BaseModelAdapter):
    name = "gemma3"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.gemma_model
        self.base_url = (
            base_url or settings.ollama_base_url
        ).rstrip("/")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
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
            return data.get("response", "")
        except Exception:
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
