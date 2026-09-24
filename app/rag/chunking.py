from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RAGChunk:
    chunk_id: str
    text: str
    source_file_id: str | None = None
    source_filename: str | None = None
    page_number: int | None = None
    section: str | None = None
    ocr_used: bool = False


class RAGChunker:
    def __init__(
        self,
        chunk_size: int = 350,
        overlap: int = 50,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if overlap < 0:
            raise ValueError("overlap cannot be negative.")

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        text: str,
        *,
        source_file_id: str | None = None,
        source_filename: str | None = None,
        page_number: int | None = None,
        section: str | None = None,
        ocr_used: bool = False,
    ) -> list[RAGChunk]:
        normalized = text.strip()

        if not normalized:
            return []

        words = normalized.split()
        step = self.chunk_size - self.overlap
        chunks: list[RAGChunk] = []

        for start in range(0, len(words), step):
            chunk_words = words[start:start + self.chunk_size]

            if not chunk_words:
                break

            chunks.append(
                RAGChunk(
                    chunk_id=f"chunk_{len(chunks) + 1:05d}",
                    text=" ".join(chunk_words),
                    source_file_id=source_file_id,
                    source_filename=source_filename,
                    page_number=page_number,
                    section=section,
                    ocr_used=ocr_used,
                )
            )

            if start + self.chunk_size >= len(words):
                break

        return chunks
