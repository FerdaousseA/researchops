from functools import lru_cache

from fastembed import TextEmbedding

from app.config import settings


@lru_cache(maxsize=1)
def get_model() -> TextEmbedding:
    return TextEmbedding(
        model_name=settings.embedding_model,
        cache_dir=settings.embedding_cache_dir,
    )


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embeddings de passages à indexer."""
    model = get_model()
    return [v.tolist() for v in model.embed(texts)]


def embed_query(text: str) -> list[float]:
    """Embedding d'une question de recherche."""
    model = get_model()
    return next(iter(model.embed([text]))).tolist()