import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
import redis
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import Base, engine, get_db
from app.ingestion import chunk_pdf
from app.embeddings import embed_passages


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


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 Mo


@app.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()

    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF valide")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 20 Mo)")

    doc_id = uuid.uuid4()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / f"{doc_id}.pdf").write_bytes(content)

    doc = models.Document(
        id=doc_id,
        filename=Path(file.filename or "document.pdf").name,
        content_type="application/pdf",
        size_bytes=len(content),
        status="pending",
    )
    db.add(doc)
    db.commit()

    return {"id": str(doc.id), "filename": doc.filename, "status": doc.status}

@app.get("/documents/{doc_id}/chunks")
def preview_chunks(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(models.Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")

    pdf_path = Path(settings.upload_dir) / f"{doc_id}.pdf"
    chunks = chunk_pdf(pdf_path)

    return {
        "filename": doc.filename,
        "total_chunks": len(chunks),
        "preview": [
            {"index": c.index, "page": c.page, "length": len(c.text), "text": c.text}
            for c in chunks[:5]
        ],
    }

@app.get("/documents/{doc_id}/embed-test")
def embed_test(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(models.Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")

    chunks = chunk_pdf(Path(settings.upload_dir) / f"{doc_id}.pdf")
    vectors = embed_passages([c.text for c in chunks])

    return {
        "total_chunks": len(chunks),
        "dimensions": len(vectors[0]) if vectors else 0,
        "first_values_of_chunk_0": vectors[0][:5] if vectors else [],
    }