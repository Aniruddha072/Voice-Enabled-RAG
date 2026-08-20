"""Qdrant-backed vector store.

One collection holds both languages, English and Hindi chunks alike,
filtered by a `language` payload field at query time rather than
split into two collections. See docs/architecture.md.

Qdrant point IDs must be an unsigned integer or a UUID, and our Chunk
IDs are descriptive strings like "1099705_hi_sentence_window_3_3", so
each point's ID is a UUID5 hash of the chunk ID (deterministic, so
re-running ingestion upserts the same points instead of duplicating
them). The original chunk ID is kept in the payload for traceability.
"""

import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from voicerag.domain.entities import Chunk, RetrievedPassage
from voicerag.domain.interfaces import VectorStore

_ID_NAMESPACE = uuid.UUID("d6f1c1e0-7e2a-4b8a-9c3d-2f6a1b8e4c9a")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, chunk_id))


class QdrantStore(VectorStore):
    def __init__(self, url: str, collection_name: str, vector_size: int) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection_name = collection_name
        self._vector_size = vector_size

    async def ensure_collection(self) -> None:
        exists = await self._client.collection_exists(self._collection_name)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self._vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    async def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        points = [
            qmodels.PointStruct(
                id=_point_id(chunk.id),
                vector=vector,
                payload=chunk.model_dump(),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection_name, points=points)

    async def search(self, vector: list[float], language: str, limit: int = 5) -> list[RetrievedPassage]:
        results = await self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            query_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="language", match=qmodels.MatchValue(value=language))]
            ),
            limit=limit,
        )
        return [
            RetrievedPassage(chunk=Chunk(**point.payload), score=point.score)
            for point in results.points
        ]
