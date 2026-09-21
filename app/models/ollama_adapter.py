from __future__ import annotations

import json
import re
from typing import Any, Callable

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.services.execution_telemetry import ExecutionTelemetry


class OllamaAdapter(BaseModelAdapter):
    name = "ollama"

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        telemetry: ExecutionTelemetry | None = None,
        performance_callback: Callable[..., None] | None = None,
    ):
        settings = get_settings()
        self.model_name = model_name
        self.base_url = base_url or settings.ollama_base_url
        self.telemetry = telemetry
        self.performance_callback = performance_callback

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
                        (
                            "http://localhost",
                            "http://127.0.0.1",
                        )
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

            # Remove explicit thinking tags if a model emits them.
            response_text = re.sub(
                r"<think>.*?</think>",
                "",
                response_text,
                flags=re.DOTALL | re.IGNORECASE,
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
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()

        try:
            return json.loads(raw)

        except json.JSONDecodeError:
            # Extract the outermost JSON object if the model
            # accidentally adds surrounding text.
            start = raw.find("{")
            end = raw.rfind("}")

            if start != -1 and end > start:
                candidate = raw[start : end + 1]

                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

            raise RuntimeError(
                f"Model '{self.model_name}' returned "
                "invalid structured JSON."
            )

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **options: Any,
    ):
        """Stream generated text chunks from Ollama."""
        import time

        started = time.perf_counter()

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": (
                system_prompt
                or "Answer directly. "
                "Return only the final answer. "
                "Do not reveal reasoning."
            ),
            "stream": True,
            "keep_alive": options.pop("keep_alive", "30m"),
            "options": {
                "num_predict": options.pop("num_predict", 2048),
                "temperature": options.pop("temperature", 0.2),
                "top_p": options.pop("top_p", 0.9),
                "top_k": options.pop("top_k", 20),
                "repeat_penalty": options.pop("repeat_penalty", 1.1),
            },
        }

        if options:
            payload["options"].update(options)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                data = json.loads(line)

                chunk = data.get("response", "")
                if chunk:
                    yield chunk

                if data.get("done"):
                    duration_ms = (time.perf_counter() - started) * 1000

                    eval_count = data.get("eval_count")
                    eval_duration = data.get("eval_duration")
                    generation_tok_s = None

                    if eval_count and eval_duration:
                        generation_tok_s = (
                            eval_count
                            / (eval_duration / 1_000_000_000)
                        )

                    metrics = {
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "prompt_eval_duration": data.get(
                            "prompt_eval_duration"
                        ),
                        "eval_duration": eval_duration,
                        "prompt_eval_count": data.get(
                            "prompt_eval_count"
                        ),
                        "eval_count": eval_count,
                        "generation_tokens_per_second": generation_tok_s,
                    }

                    if self.performance_callback is not None:
                        self.performance_callback(
                            model_name=self.model_name,
                            duration_ms=duration_ms,
                            success=True,
                            **metrics,
                        )

                    break

        except requests.RequestException as exc:
            duration_ms = (time.perf_counter() - started) * 1000

            if self.performance_callback is not None:
                self.performance_callback(
                    model_name=self.model_name,
                    duration_ms=duration_ms,
                    success=False,
                )

            raise RuntimeError(
                f"Ollama streaming request failed for model "
                f"'{self.model_name}': {exc}"
            ) from exc

        except (json.JSONDecodeError, ValueError) as exc:
            duration_ms = (time.perf_counter() - started) * 1000

            if self.performance_callback is not None:
                self.performance_callback(
                    model_name=self.model_name,
                    duration_ms=duration_ms,
                    success=False,
                )

            raise RuntimeError(
                f"Invalid Ollama streaming response for model "
                f"'{self.model_name}': {exc}"
            ) from exc

    def warm(self) -> None:
        """Load the configured model into Ollama and keep it warm."""
        self._call_ollama(
            "",
            num_predict=1,
            keep_alive="30m",
        )

    def unload(self) -> None:
        """Request Ollama to unload the configured model."""
        self._call_ollama(
            "",
            num_predict=1,
            keep_alive=0,
        )
    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not currently "
            "support direct image analysis."
        )