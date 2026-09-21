from __future__ import annotations

from typing import Any
from dataclasses import dataclass

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.models.hardware import HardwareDetector, HardwareProfile
from app.models.model_factory import ModelFactory
from app.models.model_registry import ModelDescriptor, ModelRegistry
from app.models.fallback_adapter import FallbackModelAdapter
from app.services.execution_telemetry import ExecutionTelemetry


@dataclass
class ModelPerformance:
    samples: int = 0
    generation_tokens_per_second: float = 0.0
    load_ms: float = 0.0

    def update(
        self,
        generation_tokens_per_second: float | None,
        load_ms: float | None,
    ) -> None:
        if generation_tokens_per_second is not None and generation_tokens_per_second > 0:
            self.generation_tokens_per_second = (
                (
                    self.generation_tokens_per_second * self.samples
                )
                + generation_tokens_per_second
            ) / (self.samples + 1)

        if load_ms is not None and load_ms >= 0:
            self.load_ms = (
                (
                    self.load_ms * self.samples
                )
                + load_ms
            ) / (self.samples + 1)

        self.samples += 1


class ModelGateway:
    def __init__(
        self,
        registry: ModelRegistry | None = None,
        telemetry: ExecutionTelemetry | None = None,
        hardware: HardwareProfile | None = None,
    ) -> None:
        self.registry = registry or ModelRegistry()
        self.telemetry = telemetry
        self.settings = get_settings()
        self.hardware = hardware or HardwareDetector.detect()
        self._available_model_names: set[str] | None = None
        self._performance: dict[str, ModelPerformance] = {}

    def resolve(
        self,
        task_type: str,
        *,
        telemetry: ExecutionTelemetry | None = None,
    ) -> BaseModelAdapter:
        candidates = self._rank_candidates(task_type)

        if not candidates:
            raise ValueError(
                f"No compatible model available for task type: {task_type}"
            )

        telemetry = telemetry or self.telemetry

        adapters = [
            self._create_adapter(
                descriptor,
                telemetry=telemetry,
            )
            for descriptor in candidates
        ]

        if len(adapters) == 1:
            return adapters[0]

        return FallbackModelAdapter(
            primary=adapters[0],
            fallbacks=adapters[1:],
            on_fallback=self._record_fallback,
        )

    def resolve_model(
        self,
        model_key: str,
        *,
        telemetry: ExecutionTelemetry | None = None,
    ) -> BaseModelAdapter:
        descriptor = self.registry.get(model_key)

        if not self._fits_hardware(descriptor):
            raise RuntimeError(
                f"Model '{descriptor.model_name}' exceeds available hardware capacity"
            )

        return self._create_adapter(
            descriptor,
            telemetry=telemetry or self.telemetry,
        )

    def get_descriptor(self, model_key: str) -> ModelDescriptor:
        return self.registry.get(model_key)

    def list_models(self) -> list[ModelDescriptor]:
        return self.registry.list()

    def available_models(self) -> list[ModelDescriptor]:
        self._refresh_available_models()

        return [
            model
            for model in self.registry.list()
            if model.model_name in self._available_model_names
        ]

    def is_available(self, model_key: str) -> bool:
        descriptor = self.registry.get(model_key)

        self._refresh_available_models()

        configured_model = descriptor.model_name.split(":", 1)[0]

        return any(
            available_model.split(":", 1)[0] == configured_model
            for available_model in self._available_model_names
        )

    def refresh_availability(self) -> None:
        self._available_model_names = None
        self._refresh_available_models()

    def _refresh_available_models(self) -> None:
        if self._available_model_names is not None:
            return

        try:
            response = requests.get(
                f"{self.settings.ollama_base_url}/api/tags",
                timeout=5,
            )
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])

            self._available_model_names = {
                model.get("name")
                for model in models
                if isinstance(model, dict)
                and model.get("name")
            }

        except Exception:
            self._available_model_names = set()

    def _record_model_performance(
        self,
        *,
        model_name: str,
        generation_tokens_per_second: float | None = None,
        load_ms: float | None = None,
    ) -> None:
        descriptor = next(
            (
                model
                for model in self.registry.list()
                if model.model_name == model_name
            ),
            None,
        )

        if descriptor is None:
            return

        self.record_performance(
            descriptor.key,
            generation_tokens_per_second=generation_tokens_per_second,
            load_ms=load_ms,
        )

    def record_performance(
        self,
        model_key: str,
        *,
        generation_tokens_per_second: float | None = None,
        load_ms: float | None = None,
    ) -> None:
        if generation_tokens_per_second is None and load_ms is None:
            return

        performance = self._performance.setdefault(
            model_key,
            ModelPerformance(),
        )

        performance.update(
            generation_tokens_per_second,
            load_ms,
        )

    def get_performance(
        self,
        model_key: str,
    ) -> ModelPerformance | None:
        return self._performance.get(model_key)

    def _rank_candidates(
        self,
        task_type: str,
    ) -> list[ModelDescriptor]:
        candidates = self.registry.find_by_capability(task_type)

        candidates = [
            model
            for model in candidates
            if self._fits_hardware(model)
        ]

        candidates = [
            model
            for model in candidates
            if self.is_available(model.key)
        ]

        return sorted(
            candidates,
            key=lambda model: (
                model.priority,
                -(
                    model.expected_generation_tokens_per_second
                    if model.expected_generation_tokens_per_second is not None
                    else 0.0
                ),
            ),
        )

    def _fits_hardware(
        self,
        descriptor: ModelDescriptor,
    ) -> bool:
        if self.hardware.vram_gb is None:
            return True

        return self.hardware.vram_gb >= descriptor.minimum_vram_gb

    def _create_adapter(
        self,
        descriptor: ModelDescriptor,
        *,
        telemetry: ExecutionTelemetry | None = None,
    ) -> BaseModelAdapter:
        factory_kwargs = {
            "model_name": descriptor.model_name,
            "telemetry": telemetry,
        }

        if telemetry is not None:
            factory_kwargs["performance_callback"] = (
                self._record_model_performance
            )

        if descriptor.key == "phi4-mini":
            return ModelFactory.create(
                "reasoning",
                **factory_kwargs,
            )

        if descriptor.key == "qwen2.5-coder":
            return ModelFactory.create(
                "qwen_coder",
                **factory_kwargs,
            )

        if descriptor.key == "gemma3":
            return ModelFactory.create(
                "gemma",
                **factory_kwargs,
            )

        raise ValueError(
            f"No adapter mapping for model: {descriptor.key}"
        )

    def _record_fallback(
        self,
        source_model: str,
        target_model: str,
        error: str,
    ) -> None:
        if self.telemetry is None:
            return

        self.telemetry.record_llm_call(
            model_name=target_model,
            local=True,
            duration_ms=0.0,
            success=True,
            input_chars=0,
            output_chars=0,
            fallback_from=source_model,
            fallback_error=error,
        )
