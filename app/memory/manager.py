from __future__ import annotations

import uuid
from typing import Any

from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import MemoryRetriever
from app.memory.storage import MemoryStorage


class MemoryManager:
    def __init__(
        self,
        storage: MemoryStorage | None = None,
        retriever: MemoryRetriever | None = None,
    ):
        self.storage = storage or MemoryStorage()
        self.retriever = retriever or MemoryRetriever()

    def remember(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if not content.strip():
            raise ValueError("Memory content cannot be empty")

        memory = MemoryRecord(
            memory_id=f"mem_{uuid.uuid4().hex[:12]}",
            content=content.strip(),
            memory_type=memory_type,
            metadata=metadata or {},
        )

        self.storage.save(memory)
        return memory

    def recall(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        if limit <= 0:
            return []

        memories = self.storage.list(
            memory_type=memory_type,
            limit=1000,
        )

        return self.retriever.search(
            memories=memories,
            query=query,
            limit=limit,
        )
