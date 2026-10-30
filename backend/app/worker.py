import uuid
from pathlib import Path

from celery import Celery

from app import models
from app.config import settings
from app.database import SessionLocal
from app.ingestion import chunk_pdf
from app.vectorstore import index_chunks

celery_app = Celery("researchops", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True


@celery_app.task(name="ingest_document")
def ingest_document(doc_id: str) -> dict:
    db = SessionLocal()
    try:
        doc = db.get(models.Document, uuid.UUID(doc_id))
        if doc is None:
            return {"error": "Document introuvable"}

        doc.status = "processing"
        db.commit()

        try:
            chunks = chunk_pdf(Path(settings.upload_dir) / f"{doc_id}.pdf")
            if not chunks:
                raise ValueError("Aucun texte extractible dans ce PDF")
            count = index_chunks(doc.id, doc.filename, chunks)
            doc.status = "indexed"
            db.commit()
            return {"status": "indexed", "chunks_indexed": count}
        except Exception as e:
            doc.status = "failed"
            db.commit()
            return {"status": "failed", "error": str(e)}
    finally:
        db.close()