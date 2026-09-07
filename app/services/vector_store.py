from __future__ import annotations

import hashlib
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)


class VectorStore:
    COLLECTION_NAME = "sovara_evidence"
    VECTOR_SIZE = 384

    def __init__(self, path: str = "data/qdrant"):
        self.client = QdrantClient(path=path)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = self.client.get_collections().collections

        if any(
            collection.name == self.COLLECTION_NAME
            for collection in collections
        ):
            return

        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=self.VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

    @staticmethod
    def _point_id(evidence_id: str) -> int:
        digest = hashlib.sha256(
            evidence_id.encode("utf-8")
        ).hexdigest()

        return int(digest[:15], 16)

    def get_existing(
        self,
        evidence_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not evidence_ids:
            return {}

        point_ids = [
            self._point_id(evidence_id)
            for evidence_id in evidence_ids
        ]

        results = self.client.retrieve(
            collection_name=self.COLLECTION_NAME,
            ids=point_ids,
            with_payload=True,
            with_vectors=False,
        )

        existing: dict[str, dict[str, Any]] = {}

        for result in results:
            payload = result.payload or {}
            evidence_id = payload.get("evidence_id")

            if evidence_id:
                existing[str(evidence_id)] = payload

        return existing

    def upsert_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> None:
        points: list[PointStruct] = []

        for item in evidence:
            embedding = item.get("embedding", [])
            evidence_id = item.get("evidence_id")

            if not embedding or not evidence_id:
                continue

            points.append(
                PointStruct(
                    id=self._point_id(str(evidence_id)),
                    vector=embedding,
                    payload={
                        key: value
                        for key, value in item.items()
                        if key != "embedding"
                    },
                )
            )

        if points:
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        source_file_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query_filter = None

        if source_file_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_file_id",
                        match=MatchValue(
                            value=source_file_id
                        ),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )

        return [
            {
                "score": result.score,
                **result.payload,
            }
            for result in results.points
        ]