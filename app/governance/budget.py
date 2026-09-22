from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any


class BudgetExceededError(RuntimeError):
    """Raised when an operation would exceed the execution budget."""

    def __init__(
        self,
        resource: str,
        limit: int | float,
        current: int | float,
        requested: int | float,
    ) -> None:
        self.resource = resource
        self.limit = limit
        self.current = current
        self.requested = requested

        super().__init__(
            f"Budget exceeded for {resource}: "
            f"current={current}, requested={requested}, limit={limit}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "budget_exceeded",
            "resource": self.resource,
            "limit": self.limit,
            "current": self.current,
            "requested": self.requested,
        }


@dataclass(frozen=True)
class ResourceBudget:
    max_llm_calls: int | None = None
    max_tool_calls: int | None = None
    max_retrieval_calls: int | None = None
    max_repair_attempts: int | None = None
    max_parallel_tasks: int | None = None
    max_execution_time_ms: float | None = None
    max_context_tokens: int | None = None
    max_generated_tokens: int | None = None

    def __post_init__(self) -> None:
        for field_name, value in self.__dict__.items():
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be >= 0")


@dataclass
class BudgetUsage:
    llm_calls: int = 0
    tool_calls: int = 0
    retrieval_calls: int = 0
    repair_attempts: int = 0
    parallel_tasks: int = 0
    context_tokens: int = 0
    generated_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "retrieval_calls": self.retrieval_calls,
            "repair_attempts": self.repair_attempts,
            "parallel_tasks": self.parallel_tasks,
            "context_tokens": self.context_tokens,
            "generated_tokens": self.generated_tokens,
        }


class ResourceBudgetGovernor:
    """
    Thread-safe resource governor for one agent run.

    Policy decides whether an operation is permitted.
    Approval decides whether human approval is required.
    This governor only decides whether sufficient resources remain.
    """

    def __init__(self, budget: ResourceBudget) -> None:
        self.budget = budget
        self.usage = BudgetUsage()
        self._lock = Lock()
        self._started_at = monotonic()

    def _limit_for(self, resource: str) -> int | float | None:
        return getattr(self.budget, f"max_{resource}", None)

    def _usage_for(self, resource: str) -> int | float:
        return getattr(self.usage, resource)

    def _reserve_locked(
        self,
        resource: str,
        amount: int | float,
    ) -> None:
        if amount < 0:
            raise ValueError("amount must be >= 0")

        limit = self._limit_for(resource)
        current = self._usage_for(resource)

        if limit is not None and current + amount > limit:
            raise BudgetExceededError(
                resource=resource,
                limit=limit,
                current=current,
                requested=amount,
            )

        setattr(self.usage, resource, current + amount)

    def reserve(self, resource: str, amount: int | float = 1) -> None:
        """Atomically reserve a bounded resource."""
        if resource not in self.usage.__dict__:
            raise ValueError(f"Unknown budget resource: {resource}")

        with self._lock:
            self._reserve_locked(resource, amount)

    def release(self, resource: str, amount: int | float = 1) -> None:
        """Release a previously reserved concurrent resource."""
        if resource not in self.usage.__dict__:
            raise ValueError(f"Unknown budget resource: {resource}")

        if amount < 0:
            raise ValueError("amount must be >= 0")

        with self._lock:
            current = self._usage_for(resource)
            setattr(
                self.usage,
                resource,
                max(0, current - amount),
            )

    def reserve_tool_call(self) -> None:
        self.reserve("tool_calls")

    def reserve_llm_call(self) -> None:
        self.reserve("llm_calls")

    def reserve_retrieval_call(self) -> None:
        self.reserve("retrieval_calls")

    def reserve_repair_attempt(self) -> None:
        self.reserve("repair_attempts")

    def reserve_parallel_task(self) -> None:
        self.reserve("parallel_tasks")

    def release_parallel_task(self) -> None:
        self.release("parallel_tasks")

    def reserve_context_tokens(self, tokens: int) -> None:
        self.reserve("context_tokens", tokens)

    def reserve_generated_tokens(self, tokens: int) -> None:
        self.reserve("generated_tokens", tokens)

    def check_execution_time(self) -> None:
        limit = self.budget.max_execution_time_ms

        if limit is None:
            return

        elapsed_ms = (monotonic() - self._started_at) * 1000.0

        if elapsed_ms >= limit:
            raise BudgetExceededError(
                resource="execution_time_ms",
                limit=limit,
                current=elapsed_ms,
                requested=0,
            )

    def remaining(self, resource: str) -> int | float | None:
        if resource == "execution_time_ms":
            limit = self.budget.max_execution_time_ms
            if limit is None:
                return None

            elapsed_ms = (monotonic() - self._started_at) * 1000.0
            return max(0.0, limit - elapsed_ms)

        if resource not in self.usage.__dict__:
            raise ValueError(f"Unknown budget resource: {resource}")

        limit = self._limit_for(resource)

        if limit is None:
            return None

        with self._lock:
            return max(0, limit - self._usage_for(resource))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            usage = self.usage.to_dict()

        return {
            "budget": {
                key: value
                for key, value in self.budget.__dict__.items()
            },
            "usage": usage,
            "remaining": {
                resource: self.remaining(resource)
                for resource in usage
            }
            | {
                "execution_time_ms": self.remaining(
                    "execution_time_ms"
                )
            },
        }

