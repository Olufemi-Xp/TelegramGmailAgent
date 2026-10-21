import pytest
from app.database.repositories.document_repo import DocumentRepository, cosine_similarity
from app.database.repositories.memory_repo import MemoryRepository
from app.memory.indexing import chunk_text


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0

    v4 = [0.5, 0.5, 0.0]
    assert cosine_similarity(v1, v4) > 0.7


def test_text_chunking():
    text = "Word " * 200  # 1000 characters
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) >= 3
    assert all(len(c) <= 300 for c in chunks)


@pytest.mark.asyncio
async def test_personal_memory_lifecycle(db_session):
    repo = MemoryRepository(db_session)
    user_id = 123456789

    # 1. Add facts
    mem1 = await repo.add_memory(user_id=user_id, content="User prefers Python and PostgreSQL", category="tech")
    mem2 = await repo.add_memory(user_id=user_id, content="User is located in Lagos", category="general")

    assert mem1.id is not None
    assert mem1.category == "tech"

    # 2. Search memories
    results = await repo.search_memories(user_id=user_id, query="Python")
    assert len(results) == 1
    assert "PostgreSQL" in results[0].content

    # 3. Category counts
    counts = await repo.get_category_counts(user_id=user_id)
    assert counts.get("tech") == 1
    assert counts.get("general") == 1

    # 4. Delete memory
    deleted = await repo.delete_memory(memory_id=mem1.id, user_id=user_id)
    assert deleted is True

    # 5. Verify deletion
    remaining = await repo.list_memories(user_id=user_id)
    assert len(remaining) == 1
    assert remaining[0].id == mem2.id


@pytest.mark.asyncio
async def test_document_semantic_search(db_session):
    repo = DocumentRepository(db_session)
    user_id = 123456789

    doc = await repo.create_document(
        user_id=user_id,
        filename="resume.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        storage_path="/tmp/fake_resume.pdf",
    )

    chunks = [
        {"content": "Senior Python Backend Engineer with 7 years of experience in distributed systems.", "embedding": [0.9, 0.1, 0.0]},
        {"content": "Extensive expertise in Docker, Kubernetes, and PostgreSQL optimization.", "embedding": [0.1, 0.9, 0.0]},
    ]
    await repo.add_chunks(doc.id, chunks)

    # Search with query aligned with chunk 1
    results = await repo.search_chunks_by_embedding(
        user_id=user_id,
        query_embedding=[0.9, 0.0, 0.0],
        top_k=1,
    )
    assert len(results) == 1
    chunk, score, filename = results[0]
    assert "Python Backend Engineer" in chunk.content
    assert filename == "resume.pdf"
    assert score > 0.9
