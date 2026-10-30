import uuid

from qdrant_client import QdrantClient, models

from app.config import settings
from app.embeddings import embed_passages, embed_query
from app.ingestion import Chunk

VECTOR_SIZE = 384  # doit correspondre au modèle d'embeddings

client = QdrantClient(url=settings.qdrant_url)


def ensure_collection() -> None:
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE, distance=models.Distance.COSINE
            ),
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="doc_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def index_chunks(doc_id: uuid.UUID, filename: str, chunks: list[Chunk]) -> int:
    ensure_collection()
    # réindexation propre : on supprime d'abord les anciens points du document
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id", match=models.MatchValue(value=str(doc_id))
                    )
                ]
            )
        ),
    )
    vectors = embed_passages([c.text for c in chunks])
    points = [
        models.PointStruct(
            id=str(uuid.uuid5(doc_id, str(c.index))),
            vector=vec,
            payload={
                "doc_id": str(doc_id),
                "filename": filename,
                "page": c.page,
                "chunk_index": c.index,
                "text": c.text,
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def search(query: str, limit: int = 5, doc_id: uuid.UUID | None = None):
    ensure_collection()
    query_filter = None
    if doc_id is not None:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="doc_id", match=models.MatchValue(value=str(doc_id))
                )
            ]
        )
    result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=embed_query(query),
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )
    return result.points