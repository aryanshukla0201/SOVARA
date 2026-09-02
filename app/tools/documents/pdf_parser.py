from __future__ import annotations

from typing import Any

import fitz


class PDFParser:
    @staticmethod
    def extract_text(path: str) -> dict[str, Any]:
        doc = fitz.open(path)

        pages: list[dict[str, Any]] = []

        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()

                pages.append(
                    {
                        "page_number": page_num + 1,
                        "text": text,
                    }
                )

            return {
                "pages": pages,
                "metadata": dict(doc.metadata or {}),
            }

        finally:
            doc.close()

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 350,
        overlap: int = 50,
    ) -> list[str]:
        """
        Split text into word-based chunks with overlap.

        Overlap helps preserve context when relevant information
        spans a chunk boundary.
        """

        words = text.split()

        if not words:
            return []

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if overlap < 0:
            raise ValueError("overlap cannot be negative.")

        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")

        chunks: list[str] = []

        step = chunk_size - overlap

        for start in range(0, len(words), step):
            chunk_words = words[start:start + chunk_size]

            if not chunk_words:
                break

            chunks.append(" ".join(chunk_words))

            if start + chunk_size >= len(words):
                break

        return chunks