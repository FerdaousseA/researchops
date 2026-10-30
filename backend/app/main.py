from contextlib import asynccontextmanager

import psycopg
import redis
from fastapi import Depends, FastAPI
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="ResearchOps API", lifespan=lifespan)


@app.get("/health")
def health():
    status = {}

    try:
        with psycopg.connect(
            host=settings.postgres_host,
            user=settings.postgres_user,
            password=settings.postgres_password,
            dbname=settings.postgres_db,
        ) as conn:
            conn.execute("SELECT 1")
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {e}"

    try:
        redis.from_url(settings.redis_url).ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"

    try:
        QdrantClient(url=settings.qdrant_url).get_collections()
        status["qdrant"] = "ok"
    except Exception as e:
        status["qdrant"] = f"error: {e}"

    return status


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(select(models.Document).order_by(models.Document.created_at.desc()))
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status,
            "size_bytes": d.size_bytes,
            "created_at": d.created_at,
        }
        for d in docs
    ]