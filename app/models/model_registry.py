from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from app.core.config import get_settings


@dataclass(frozen=True)
class ModelDescriptor:
    key: str
    model_name: str
    capabilities: FrozenSet[str]
    priority: int = 100
    minimum_vram_gb: float = 0.0
    expected_generation_tokens_per_second: float | None = None
    expected_load_ms: float | None = None


class ModelRegistry:
    def __init__(self) -> None:
        settings = get_settings()

        self._models: dict[str, ModelDescriptor] = {
            "phi4-mini": ModelDescriptor(
                key="phi4-mini",
                model_name="phi4-mini:latest",
                capabilities=frozenset({
                    "reasoning",
                    "summarization",
                    "task_analysis",
                    "document_analysis",
                    "general",
                }),
                priority=100,
                minimum_vram_gb=4.0,
                expected_generation_tokens_per_second=63.7,
                expected_load_ms=5300.0,
            ),
            "qwen2.5-coder": ModelDescriptor(
                key="qwen2.5-coder",
                model_name="qwen2.5-coder:7b-instruct",
                capabilities=frozenset({
                    "code_generation",
                    "code_analysis",
                    "code",
                }),
                priority=100,
                minimum_vram_gb=6.0,
                expected_generation_tokens_per_second=43.9,
                expected_load_ms=13150.0,
            ),
            "gemma3": ModelDescriptor(
                key="gemma3",
                model_name=settings.gemma_model,
                capabilities=frozenset({
                    "vision",
                    "vision_analysis",
                    "multimodal_understanding",
                }),
                priority=100,
                minimum_vram_gb=4.0,
                expected_generation_tokens_per_second=55.1,
                expected_load_ms=8914.0,
            ),
        }

    def get(self, key: str) -> ModelDescriptor:
        try:
            return self._models[key]
        except KeyError as exc:
            raise KeyError(f"Unknown model: {key}") from exc

    def list(self) -> list[ModelDescriptor]:
        return list(self._models.values())

    def find_by_capability(
        self,
        capability: str,
    ) -> list[ModelDescriptor]:
        matches = [
            model
            for model in self._models.values()
            if capability in model.capabilities
        ]

        return sorted(
            matches,
            key=lambda model: model.priority,
        )
