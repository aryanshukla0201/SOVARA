from __future__ import annotations

import json
from typing import Any

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter


class GemmaAdapter(BaseModelAdapter):
    name = "gemma3"

    def __init__(self, model_name: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.gemma_model
        self.base_url = base_url or settings.ollama_base_url

    def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
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

    def generate_structured(self, prompt: str, schema: Any, system_prompt: str | None = None, **kwargs: Any) -> dict[str, Any]:
        raw = self.generate(prompt, system_prompt=system_prompt)
        try:
            return json.loads(raw)
        except Exception:
            return {"observations": [{"description": "Vision fallback", "confidence": 0.5}]}

    def analyze_image(self, image_path: str, task_context: str) -> dict[str, Any]:
        return {
            "image_id": image_path.split("/")[-1],
            "observations": [
                {
                    "description": f"Vision context: {task_context}",
                    "confidence": 0.8,
                }
            ],
        }
