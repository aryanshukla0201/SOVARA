from __future__ import annotations

import os

os.environ["FLAGS_use_mkldnn"] = "0"

from typing import Any

import fitz
from paddleocr import PaddleOCR


class PDFParser:
    _ocr = None

    @classmethod
    def _get_ocr(cls) -> PaddleOCR:
        if cls._ocr is None:
            cls._ocr = PaddleOCR(
                lang="en",
                enable_mkldnn=False,
            )
        return cls._ocr

    @classmethod
    def _ocr_page(cls, page: fitz.Page) -> str:
        import tempfile
        from pathlib import Path

        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False,
        )

        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            pixmap.save(str(temp_path))

            result = cls._get_ocr().predict(input=str(temp_path))

            text_parts: list[str] = []

            for item in result:
                texts = getattr(item, "rec_texts", None)

                if texts is None and isinstance(item, dict):
                    texts = item.get("rec_texts", [])

                if isinstance(texts, list):
                    text_parts.extend(
                        str(text).strip()
                        for text in texts
                        if str(text).strip()
                    )

            return "\n".join(text_parts)

        finally:
            temp_path.unlink(missing_ok=True)

    @classmethod
    def extract_text(cls, path: str) -> dict[str, Any]:
        doc = fitz.open(path)

        pages: list[dict[str, Any]] = []

        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text().strip()

                needs_ocr = len(text) < 20

                if needs_ocr:
                    try:
                        ocr_text = cls._ocr_page(page)

                        if ocr_text.strip():
                            text = ocr_text.strip()

                    except Exception as exc:
                        print(
                            f"[OCR WARNING] "
                            f"Page {page_num + 1}: {exc}"
                        )

                pages.append(
                    {
                        "page_number": page_num + 1,
                        "text": text,
                        "needs_ocr": needs_ocr,
                        "ocr_used": needs_ocr and bool(text),
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

        words = text.split()

        if not words:
            return []

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if overlap < 0:
            raise ValueError("overlap cannot be negative.")

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

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