from __future__ import annotations

from typing import Any, Callable

from app.models.base import BaseModelAdapter
from app.governance.budget import BudgetExceededError


class ModelExecutionError(RuntimeError):
    """Raised when a model invocation fails and may be retried."""


class FallbackModelAdapter(BaseModelAdapter):
    """
    Executes a primary model and retries with compatible fallback adapters.

    Fallbacks are supplied explicitly by the gateway. This class never
    changes task capability requirements itself.
    """

    def __init__(
        self,
        primary: BaseModelAdapter,
        fallbacks: list[BaseModelAdapter] | None = None,
        on_fallback: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks or []
        self.on_fallback = on_fallback
        self.name = primary.name

    def _candidates(self) -> list[BaseModelAdapter]:
        return [self.primary, *self.fallbacks]

    def _execute(
        self,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        candidates = self._candidates()
        last_error: Exception | None = None

        for index, adapter in enumerate(candidates):
            try:
                return getattr(adapter, method)(*args, **kwargs)
            except BudgetExceededError:
                raise
            except RuntimeError as exc:
                last_error = exc

                if index >= len(candidates) - 1:
                    break

                fallback = candidates[index + 1]

                if self.on_fallback is not None:
                    self.on_fallback(
                        adapter.name,
                        fallback.name,
                        str(exc),
                    )

        if last_error is not None:
            raise last_error

        raise RuntimeError("No model adapters configured")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        return self._execute(
            "generate",
            prompt,
            system_prompt=system_prompt,
            **kwargs,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._execute(
            "generate_structured",
            prompt,
            schema,
            system_prompt=system_prompt,
            **kwargs,
        )

    def analyze_image(
        self,
        image_path: str,
        task_context: str,
    ) -> dict[str, Any]:
        return self._execute(
            "analyze_image",
            image_path,
            task_context,
        )
