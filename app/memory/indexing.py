import csv
import io
import os
from typing import Any, Dict, List, Tuple
from pypdf import PdfReader
import docx
from app.config import settings
from app.database.repositories.document_repo import DocumentRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.providers.embeddings.provider import embedding_service

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
    reader = PdfReader(file_path)
    page_count = len(reader.pages)
    text_parts = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        text_parts.append(f"[Page {i+1}]\n{page_text}")
    return "\n\n".join(text_parts), page_count


def extract_text_from_docx(file_path: str) -> Tuple[str, int]:
    doc = docx.Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs), 1


def extract_text_from_txt(file_path: str) -> Tuple[str, int]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return content, 1


def extract_text_from_csv(file_path: str) -> Tuple[str, int]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        lines = [", ".join(row) for row in reader]
    return "\n".join(lines), 1


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Splits long text into overlapping chunks."""
    if not text.strip():
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start += chunk_size - overlap
    return chunks


class DocumentIndexer:
    @staticmethod
    async def index_file(user_id: int, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Extracts text, creates chunks, computes embeddings, and indexes document into DB."""
        ext = os.path.splitext(original_filename)[1].lower()
        file_size = os.path.getsize(file_path)

        # Enforce file size limit
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB.")

        # Extract text based on extension
        if ext == ".pdf":
            raw_text, page_count = extract_text_from_pdf(file_path)
        elif ext == ".docx":
            raw_text, page_count = extract_text_from_docx(file_path)
        elif ext in (".txt", ".md"):
            raw_text, page_count = extract_text_from_txt(file_path)
        elif ext == ".csv":
            raw_text, page_count = extract_text_from_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: .pdf, .docx, .txt, .csv, .md")

        if not raw_text.strip():
            raise ValueError(f"Could not extract any readable text from '{original_filename}'.")

        # Chunk text
        chunks = chunk_text(raw_text, chunk_size=600, overlap=100)
        if not chunks:
            raise ValueError("Document yielded no text chunks.")

        # Compute embeddings
        embeddings = await embedding_service.get_embeddings_batch(chunks)

        chunk_records = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_records.append({
                "content": chunk,
                "metadata": {"source": original_filename, "chunk_index": i},
                "embedding": emb,
            })

        async with get_db_session() as session:
            repo = DocumentRepository(session)
            doc = await repo.create_document(
                user_id=user_id,
                filename=original_filename,
                file_type=ext.replace(".", ""),
                file_size_bytes=file_size,
                storage_path=file_path,
                page_count=page_count,
            )
            total_chunks = await repo.add_chunks(doc.id, chunk_records)

        logger.info(f"Indexed document '{original_filename}' (id={doc.id}): {total_chunks} chunks.")
        return {
            "document_id": doc.id,
            "filename": original_filename,
            "chunk_count": total_chunks,
            "page_count": page_count,
            "file_size_bytes": file_size,
        }
