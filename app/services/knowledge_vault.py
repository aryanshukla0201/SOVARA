from __future__ import annotations

import hashlib
import shutil
import sqlite3
import uuid
from pathlib import Path

from app.tools.documents.docx_parser import DOCXParser
from app.tools.documents.pdf_parser import PDFParser
from app.tools.documents.retriever import DocumentRetriever
from app.state.evidence import EvidenceRecord


class KnowledgeVault:
    def __init__(
        self,
        retriever: DocumentRetriever | None = None,
    ):
        self.db_path = Path("data/sovara.db")
        self.storage_dir = Path("data/vault")
        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.retriever = retriever or DocumentRetriever()
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vault_documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    @staticmethod
    def _hash_file(file_path: str | Path) -> str:
        path = Path(file_path)
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    def _update_status(self, document_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE vault_documents
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE document_id = ?
                """,
                (status, document_id),
            )
            conn.commit()

    def _parse_document(self, file_path: Path, file_type: str) -> list[dict]:
        if file_type == "pdf":
            parsed = PDFParser.extract_text(file_path)

            chunks = []

            for page in parsed["pages"]:
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

            return chunks

        if file_type == "docx":
            parsed = DOCXParser.extract_text(file_path)
            return DOCXParser.chunk_text(parsed["text"])

        raise ValueError(f"Unsupported file type: {file_type}")

    def add_document(
        self,
        file_path: str | Path,
        file_type: str,
    ) -> dict:
        source_path = Path(file_path)

        if not source_path.exists():
            raise FileNotFoundError(source_path)

        content_hash = self._hash_file(source_path)

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT document_id, filename, file_path,
                       file_type, content_hash, status
                FROM vault_documents
                WHERE content_hash = ?
                """,
                (content_hash,),
            ).fetchone()

        if existing:
            return {
                "document_id": existing[0],
                "filename": existing[1],
                "file_path": existing[2],
                "file_type": existing[3],
                "content_hash": existing[4],
                "status": existing[5],
                "already_exists": True,
            }

        document_id = f"doc_{uuid.uuid4().hex[:12]}"

        extension = source_path.suffix.lower()
        destination = (
            self.storage_dir
            / f"{document_id}{extension}"
        )

        shutil.copy2(source_path, destination)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO vault_documents (
                    document_id,
                    filename,
                    file_path,
                    file_type,
                    content_hash,
                    status
                )
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (
                    document_id,
                    source_path.name,
                    str(destination),
                    file_type,
                    content_hash,
                ),
            )
            conn.commit()

        try:
            chunks = self._parse_document(
                destination,
                file_type,
            )

            if not chunks:
                raise ValueError("No extractable content found")

            self.retriever.retrieve(
                chunks=chunks,
                query="",
                file_id=document_id,
                filename=source_path.name,
            )

            self._update_status(
                document_id,
                "indexed",
            )

        except Exception:
            self._update_status(
                document_id,
                "failed",
            )
            raise

        return {
            "document_id": document_id,
            "filename": source_path.name,
            "file_path": str(destination),
            "file_type": file_type,
            "content_hash": content_hash,
            "status": "indexed",
            "already_exists": False,
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list:
        from app.services.embedding_service import EmbeddingService

        query_embedding = EmbeddingService.embed_text(query)

        if not query_embedding:
            return []

        documents = self.list_documents()
        results = []

        for document in documents:
            if document["status"] != "indexed":
                continue

            qdrant_results = self.retriever.vector_store.search(
                query_vector=query_embedding,
                limit=top_k,
                source_file_id=document["document_id"],
            )

            for item in qdrant_results:
                score = float(item.get("score", 0.0))

                if score < self.retriever.min_score:
                    continue

                results.append(
                    EvidenceRecord(
                        evidence_id=(
                            f"{item.get('source_file_id')}_ev_000"
                        ),
                        source_file_id=item.get(
                            "source_file_id",
                            "",
                        ),
                        source_filename=item.get(
                            "source_filename",
                            "",
                        ),
                        page_number=item.get("page_number"),
                        chunk_id=item.get("chunk_id"),
                        text=item.get("content", ""),
                        relevance_score=round(score, 4),
                        retrieval_method=(
                            "pdf_ocr"
                            if item.get("ocr_used", False)
                            else "semantic_qdrant"
                        ),
                    )
                )

        results.sort(
            key=lambda item: item.relevance_score,
            reverse=True,
        )

        for index, item in enumerate(results[:top_k], start=1):
            item.evidence_id = (
                f"{item.source_file_id}_ev_{index:03d}"
            )

        return results[:top_k]

    def get_document(
        self,
        document_id: str,
    ) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT document_id, filename, file_path,
                       file_type, content_hash, status,
                       created_at, updated_at
                FROM vault_documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "document_id": row[0],
            "filename": row[1],
            "file_path": row[2],
            "file_type": row[3],
            "content_hash": row[4],
            "status": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }

    def reindex_document(self, document_id: str) -> dict:
        document = self.get_document(document_id)

        if document is None:
            raise FileNotFoundError(
                f"Vault document not found: {document_id}"
            )

        file_path = Path(document["file_path"])

        if not file_path.exists():
            raise FileNotFoundError(file_path)

        self.retriever.vector_store.delete_by_source_file_id(
            document_id
        )

        self._update_status(document_id, "pending")

        try:
            chunks = self._parse_document(
                file_path,
                document["file_type"],
            )

            if not chunks:
                raise ValueError("No extractable content found")

            self.retriever.retrieve(
                chunks=chunks,
                query="",
                file_id=document_id,
                filename=document["filename"],
            )

            self._update_status(document_id, "indexed")

        except Exception:
            self._update_status(document_id, "failed")
            raise

        updated = self.get_document(document_id)

        return {
            **updated,
            "reindexed": True,
        }


    def delete_document(self, document_id: str) -> bool:
        document = self.get_document(document_id)

        self.retriever.vector_store.delete_by_source_file_id(document_id)

        if document is None:
            orphaned_files = list(
                self.storage_dir.glob(f"{document_id}.*")
            )
            for file_path in orphaned_files:
                if file_path.exists():
                    file_path.unlink()
            return False

        with self._connect() as conn:
            conn.execute(
                "DELETE FROM vault_documents WHERE document_id = ?",
                (document_id,),
            )
            conn.commit()

        file_path = Path(document["file_path"])
        if file_path.exists():
            file_path.unlink()

        return True

    def list_documents(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, filename, file_path,
                       file_type, content_hash, status,
                       created_at, updated_at
                FROM vault_documents
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [
            {
                "document_id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "file_type": row[3],
                "content_hash": row[4],
                "status": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]