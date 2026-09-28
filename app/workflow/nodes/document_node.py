from __future__ import annotations

from pathlib import Path

from app.tools.documents.pdf_parser import PDFParser
from app.tools.documents.docx_parser import DOCXParser
from app.tools.documents.retriever import DocumentRetriever
from app.state.evidence import EvidenceRecord


class DocumentNode:
    def __init__(self, retriever: DocumentRetriever):
        self.retriever = retriever

    def run(
        self,
        file_path: str,
        user_query: str,
        file_id: str,
        file_type: str = "pdf",
    ) -> list:

        filename = Path(file_path).name

        # ---------------------------------------------------------
        # PDF
        # ---------------------------------------------------------
        if file_type == "pdf":
            parsed_document = PDFParser.extract_text(file_path)

            if parsed_document.get("error"):
                return [
                    EvidenceRecord(
                        evidence_id=f"{file_id}_error",
                        source_file_id=file_id,
                        source_filename=filename,
                        page_number=None,
                        chunk_id="document_error",
                        text=(
                            f"Unable to parse PDF '{filename}': "
                            f"{parsed_document['error']}"
                        ),
                        relevance_score=1.0,
                        retrieval_method="parser_error",
                    )
                ]

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

        # ---------------------------------------------------------
        # DOCX
        # ---------------------------------------------------------
        elif file_type == "docx":
            parsed_document = DOCXParser.extract_text(file_path)

            chunks = DOCXParser.chunk_text(
                parsed_document["text"]
            )

        # ---------------------------------------------------------
        # UNSUPPORTED
        # ---------------------------------------------------------
        else:
            return []

        return self.retriever.retrieve(
            chunks=chunks,
            query=user_query,
            file_id=file_id,
            filename=filename,
        )