from __future__ import annotations

import hashlib

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.state.evidence import EvidenceRecord


class DocumentRetriever:
    def __init__(
        self,
        top_k: int = 5,
        min_score: float = 0.05,
    ):
        self.top_k = top_k
        self.min_score = min_score
        self.vector_store = VectorStore()

    @staticmethod
    def _content_hash(text: str) -> str:
        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    def retrieve(
        self,
        chunks: list[dict],
        query: str,
        file_id: str,
        filename: str,
    ) -> list[EvidenceRecord]:

        evidence_for_indexing: list[dict] = []

        for index, chunk in enumerate(chunks, start=1):
            text = chunk.get("text", "").strip()

            if not text:
                continue

            evidence_for_indexing.append(
                {
                    "evidence_id": (
                        f"{file_id}_chunk_{index:05d}"
                    ),
                    "source_file_id": file_id,
                    "source_filename": filename,
                    "evidence_type": "document",
                    "content": text,
                    "content_hash": self._content_hash(text),
                    "embedding_model": EmbeddingService.MODEL_NAME,
                    "page_number": chunk.get("page_number"),
                    "chunk_id": chunk.get("chunk_id"),
                    "ocr_used": bool(
                        chunk.get("ocr_used", False)
                    ),
                }
            )

        if not evidence_for_indexing:
            return []

        evidence_ids = [
            item["evidence_id"]
            for item in evidence_for_indexing
        ]

        existing = self.vector_store.get_existing(
            evidence_ids
        )

        items_to_embed: list[dict] = []

        for item in evidence_for_indexing:
            evidence_id = item["evidence_id"]
            stored = existing.get(evidence_id)

            if stored is None:
                items_to_embed.append(item)
                continue

            if (
                stored.get("content_hash") != item["content_hash"]
                or stored.get("embedding_model") != item["embedding_model"]
            ):
                items_to_embed.append(item)

        if items_to_embed:

            print(
                f"[RETRIEVAL CACHE] embedding "
                f"{len(items_to_embed)} new/changed chunks"
            )

            embedded = EmbeddingService.embed_evidence(
                items_to_embed
            )

            self.vector_store.upsert_evidence(
                embedded
            )

        else:
            print(
                "[RETRIEVAL CACHE] all chunks already indexed; "
                "skipping embedding"
            )

        query_vector = EmbeddingService.embed_text(query)

        if not query_vector:
            return []

        results = self.vector_store.search(
            query_vector=query_vector,
            limit=self.top_k,
            source_file_id=file_id,
        )

        evidence: list[EvidenceRecord] = []

        for index, item in enumerate(results, start=1):
            score = float(
                item.get("score", 0.0)
            )

            if score < self.min_score:
                continue

            ocr_used = bool(
                item.get("ocr_used", False)
            )

            evidence.append(
                EvidenceRecord(
                    evidence_id=(
                        f"{file_id}_ev_{index:03d}"
                    ),
                    source_file_id=file_id,
                    source_filename=(
                        item.get("source_filename")
                        or filename
                    ),
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                    text=item.get("content", ""),
                    relevance_score=round(
                        score,
                        4,
                    ),
                    retrieval_method=(
                        "pdf_ocr"
                        if ocr_used
                        else "semantic_qdrant"
                    ),
                )
            )

        return evidence