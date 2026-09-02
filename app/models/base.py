from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseModelAdapter(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Any, system_prompt: str | None = None, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def analyze_image(self, image_path: str, task_context: str) -> dict[str, Any]:
        raise NotImplementedError
