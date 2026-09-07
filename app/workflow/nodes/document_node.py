from __future__ import annotations

from pathlib import Path

from app.tools.documents.pdf_parser import PDFParser
from app.tools.documents.retriever import DocumentRetriever


class DocumentNode:
    def __init__(self, retriever: DocumentRetriever):
        self.retriever = retriever

    def run(
        self,
        pdf_path: str,
        user_query: str,
        file_id: str,
    ) -> list:
        parsed_document = PDFParser.extract_text(pdf_path)

        chunks = []

        for page in parsed_document["pages"]:
            page_number = page["page_number"]
            page_text = page["text"]
            ocr_used = page.get("ocr_used", False)

            page_chunks = PDFParser.chunk_text(page_text)

            for chunk_index, chunk_text in enumerate(
                page_chunks,
                start=1,
            ):
                chunks.append(
                    {
                        "page_number": page_number,
                        "chunk_id": (
                            f"page_{page_number}_chunk_{chunk_index}"
                        ),
                        "text": chunk_text,
                        "ocr_used": ocr_used,
                    }
                )

        filename = Path(pdf_path).name

        return self.retriever.retrieve(
            chunks=chunks,
            query=user_query,
            file_id=file_id,
            filename=filename,
        )