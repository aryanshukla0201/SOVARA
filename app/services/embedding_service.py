from __future__ import annotations

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _model = None

    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    @classmethod
    def _get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer(cls.MODEL_NAME)

        return cls._model

    @classmethod
    def embed_text(cls, text: str) -> list[float]:
        if not text.strip():
            return []

        embedding = cls._get_model().encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    @classmethod
    def embed_texts(
        cls,
        texts: list[str],
    ) -> list[list[float]]:
        valid_texts = [
            text.strip()
            for text in texts
            if text and text.strip()
        ]

        if not valid_texts:
            return []

        embeddings = cls._get_model().encode(
            valid_texts,
            normalize_embeddings=True,
            batch_size=16,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    @classmethod
    def embed_evidence(
        cls,
        evidence: list[dict],
    ) -> list[dict]:
        valid_items = [
            item
            for item in evidence
            if item.get("content", "").strip()
        ]

        if not valid_items:
            return evidence

        texts = [
            item["content"]
            for item in valid_items
        ]

        embeddings = cls.embed_texts(texts)

        embedding_index = 0

        for item in evidence:
            content = item.get("content", "")

            if not content.strip():
                item["embedding"] = []
                continue

            item["embedding"] = embeddings[
                embedding_index
            ]

            embedding_index += 1

        return evidence