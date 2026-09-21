from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from threading import Lock

from app.governance.audit import AuditEvent


@dataclass
class Observability:
    _events: list[AuditEvent] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def get_events(self, task_id: str) -> list[AuditEvent]:
        with self._lock:
            return [
                event
                for event in self._events
                if event.task_id == task_id
            ]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def metrics(self) -> dict[str, int]:
        with self._lock:
            counts = Counter(event.event_type for event in self._events)

        return {
            "execution_started": counts["execution_started"],
            "execution_completed": counts["execution_completed"],
            "execution_failed": counts["execution_failed"],
            "policy_denied": counts["policy_denied"],
            "tool_invocation_count": counts["execution_started"],
        }
