from __future__ import annotations

from dataclasses import dataclass

import tiktoken


@dataclass
class ContextManager:
    max_context_tokens: int = 6144
    max_evidence_items: int = 5

    def __post_init__(self) -> None:
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def _reserve_query(self, user_query: str) -> tuple[str, int]:
        query_block = f"USER REQUEST:\n{user_query}"
        return query_block, self.count_tokens(query_block)

    def build_prompt_context(
        self,
        user_query: str,
        conversation_history: list[dict] | None = None,
        evidence: list[dict] | None = None,
    ) -> str:
        history = conversation_history or []
        evidence = evidence or []

        query_block, query_tokens = self._reserve_query(user_query)

        if query_tokens >= self.max_context_tokens:
            return query_block

        sections: list[str] = []
        used_tokens = query_tokens
        available_tokens = self.max_context_tokens - query_tokens

        for message in reversed(history):
            role = message.get("role", "user")
            content = str(message.get("content", "")).strip()

            if not content:
                continue

            block = f"{role.upper()}:\n{content}"
            tokens = self.count_tokens(block)

            if used_tokens + tokens > self.max_context_tokens:
                break

            sections.insert(0, block)
            used_tokens += tokens

        evidence_blocks: list[str] = []

        for item in evidence[:self.max_evidence_items]:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")
            if not evidence_id:
                continue

            content = item.get("content", item.get("text", ""))

            if not content:
                continue

            block = (
                f"EVIDENCE ID: {evidence_id}\n"
                f"TYPE: {item.get('evidence_type', 'document')}\n"
                f"SOURCE: {item.get('source_filename', '')}\n"
                f"PAGE: {item.get('page_number', '')}\n\n"
                f"CONTENT:\n{content}"
            )

            tokens = self.count_tokens(block)

            if used_tokens + tokens > self.max_context_tokens:
                break

            evidence_blocks.append(block)
            used_tokens += tokens

        if evidence_blocks:
            sections.append(
                "AUTHORITATIVE EVIDENCE:\n\n"
                + "\n\n".join(evidence_blocks)
            )

        sections.append(query_block)

        return "\n\n".join(sections)

    def build_prompt_from_blocks(
        self,
        user_query: str,
        context_blocks: list[str],
        conversation_history: list[dict] | None = None,
    ) -> str:
        history = conversation_history or []

        query_block, query_tokens = self._reserve_query(user_query)

        if query_tokens >= self.max_context_tokens:
            return query_block

        sections: list[str] = []
        used_tokens = query_tokens

        for message in reversed(history):
            role = message.get("role", "user")
            content = str(message.get("content", "")).strip()

            if not content:
                continue

            block = f"{role.upper()}:\n{content}"
            tokens = self.count_tokens(block)

            if used_tokens + tokens > self.max_context_tokens:
                break

            sections.insert(0, block)
            used_tokens += tokens

        for block in context_blocks:
            tokens = self.count_tokens(block)

            if used_tokens + tokens > self.max_context_tokens:
                break

            sections.append(block)
            used_tokens += tokens

        sections.append(query_block)

        return "\n\n".join(sections)

    def build_context(
        self,
        user_query: str,
        conversation_history: list[dict] | None = None,
        retrieved_evidence: list[dict] | None = None,
    ) -> list[dict]:
        return [
            {
                "role": "user",
                "content": self.build_prompt_context(
                    user_query=user_query,
                    conversation_history=conversation_history,
                    evidence=retrieved_evidence,
                ),
            }
        ]