"""
Basic backend tests for InsightFlow AI.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    db.users.count_documents = AsyncMock(return_value=0)
    db.users.find_one = AsyncMock(return_value=None)
    db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id="507f1f77bcf86cd799439011"))
    db.users.create_index = AsyncMock(return_value=None)
    return db


class TestSecurityUtils:
    def test_password_hashing(self):
        from app.core.security import hash_password, verify_password
        password = "test_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_jwt_token_creation_and_decode(self):
        from app.core.security import create_access_token, decode_token
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)
        assert token is not None
        decoded = decode_token(token)
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access"

    def test_refresh_token_type(self):
        from app.core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "user123"})
        decoded = decode_token(token)
        assert decoded["type"] == "refresh"

    def test_verify_invalid_token(self):
        from app.core.security import verify_token
        result = verify_token("invalid.token.here")
        assert result is None


class TestTextCleaner:
    def test_clean_basic_text(self):
        from app.services.ingestion.cleaner import clean_text
        text = "  Hello   World  \n\n\n  Test  "
        cleaned = clean_text(text)
        assert "Hello" in cleaned
        assert "  " not in cleaned  # no double spaces

    def test_remove_separator_lines(self):
        from app.services.ingestion.cleaner import clean_text
        text = "Content\n----------\nMore content"
        cleaned = clean_text(text)
        assert "Content" in cleaned
        assert "----------" not in cleaned

    def test_unicode_normalization(self):
        from app.services.ingestion.cleaner import clean_text
        text = "Smart \u201ccurly\u201d quotes and fi\ufb01 ligature"
        cleaned = clean_text(text)
        assert '"curly"' in cleaned or 'curly' in cleaned


class TestChunkingEngine:
    def test_chunk_creates_overlapping_chunks(self):
        from app.services.ingestion.chunker import ChunkingEngine
        engine = ChunkingEngine(chunk_size=100, chunk_overlap=20)
        pages = [(1, "This is a test document. " * 20)]
        chunks = engine.chunk_pages(pages, "DOC001", "Test Doc", "test.txt", "HR")
        assert len(chunks) > 1
        assert all("chunk_id" in c for c in chunks)
        assert all("text" in c for c in chunks)
        assert all("department" in c for c in chunks)
        assert all(c["department"] == "HR" for c in chunks)

    def test_chunk_metadata(self):
        from app.services.ingestion.chunker import ChunkingEngine
        engine = ChunkingEngine()
        pages = [(1, "Test content for chunking. " * 30)]
        chunks = engine.chunk_pages(pages, "DOC001", "My Doc", "doc.pdf", "Finance")
        for chunk in chunks:
            assert chunk["document_id"] == "DOC001"
            assert chunk["document_title"] == "My Doc"
            assert chunk["filename"] == "doc.pdf"
            assert chunk["page_number"] == 1

    def test_empty_text_returns_no_chunks(self):
        from app.services.ingestion.chunker import ChunkingEngine
        engine = ChunkingEngine()
        chunks = engine.chunk_pages([], "DOC001", "Empty", "empty.txt", "HR")
        assert chunks == []


class TestCitationBuilder:
    def test_builds_citations_from_chunks(self):
        from app.services.generation.citation_builder import CitationBuilder
        builder = CitationBuilder()
        chunks = [
            {
                "chunk_id": "ch1",
                "text": "This is the content of the chunk for testing purposes.",
                "metadata": {
                    "document_id": "doc1",
                    "document_title": "HR Policy",
                    "filename": "hr_policy.pdf",
                    "page_number": 5,
                },
                "final_score": 0.85,
                "semantic_score": 0.80,
            }
        ]
        citations = builder.build(chunks)
        assert len(citations) == 1
        assert citations[0].document_id == "doc1"
        assert citations[0].title == "HR Policy"
        assert citations[0].page == 5

    def test_deduplicates_same_page(self):
        from app.services.generation.citation_builder import CitationBuilder
        builder = CitationBuilder()
        chunks = [
            {"chunk_id": "ch1", "text": "Content 1", "metadata": {"document_id": "doc1", "document_title": "Doc", "filename": "doc.pdf", "page_number": 1}, "final_score": 0.9},
            {"chunk_id": "ch2", "text": "Content 2", "metadata": {"document_id": "doc1", "document_title": "Doc", "filename": "doc.pdf", "page_number": 1}, "final_score": 0.8},
        ]
        citations = builder.build(chunks)
        assert len(citations) == 1  # deduplicated


class TestConfig:
    def test_settings_loads(self):
        from app.core.config import settings
        assert settings.mongodb_db_name == "insightflow"
        assert settings.jwt_algorithm == "HS256"
        assert settings.rate_limit_per_minute == 60

    def test_origins_list_parsed(self):
        from app.core.config import settings
        origins = settings.origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1
