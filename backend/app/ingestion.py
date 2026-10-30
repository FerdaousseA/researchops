from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


@dataclass
class Chunk:
    index: int
    page: int
    text: str


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Retourne une liste de (numéro_de_page, texte), pages vides ignorées."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    return pages


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Découpe un texte en morceaux de ~size caractères avec chevauchement,
    en essayant de couper sur une fin de phrase ou un espace."""
    text = " ".join(text.split())  # normalise les espaces et retours à la ligne
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # cherche une coupure propre dans le dernier quart du chunk
            cut = max(text.rfind(". ", start, end), text.rfind(" ", start, end))
            if cut > start + size * 0.75:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_pdf(pdf_path: Path) -> list[Chunk]:
    chunks = []
    index = 0
    for page_number, page_text in extract_pages(pdf_path):
        for piece in split_text(page_text):
            chunks.append(Chunk(index=index, page=page_number, text=piece))
            index += 1
    return chunks