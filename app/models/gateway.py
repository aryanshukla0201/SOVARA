from __future__ import annotations

from typing import Any

import requests

from app.core.config import get_settings
from app.models.base import BaseModelAdapter
from app.models.hardware import HardwareDetector, HardwareProfile
from app.models.model_factory import ModelFactory
from app.models.model_registry import ModelDescriptor, ModelRegistry
from app.services.execution_telemetry import ExecutionTelemetry


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

        return self._create_adapter(
            candidates[0],
            telemetry=telemetry or self.telemetry,
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

        return descriptor.model_name in self._available_model_names

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
            key=lambda model: model.priority,
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
        if descriptor.key == "phi4-mini":
            return ModelFactory.create(
                "reasoning",
                model_name=descriptor.model_name,
                telemetry=telemetry,
            )

        if descriptor.key == "qwen2.5-coder":
            return ModelFactory.create(
                "qwen_coder",
                model_name=descriptor.model_name,
                telemetry=telemetry,
            )

        if descriptor.key == "gemma3":
            return ModelFactory.create(
                "gemma",
                model_name=descriptor.model_name,
                telemetry=telemetry,
            )

        raise ValueError(
            f"No adapter mapping for model: {descriptor.key}"
        )
