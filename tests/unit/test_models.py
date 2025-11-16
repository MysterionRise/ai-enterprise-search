"""Unit tests for data models"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.documents import Document, DocumentChunk, DocumentIngestRequest
from src.models.search import SearchRequest, SearchFilters
from src.models.auth import User, UserCreate, Token


class TestDocumentModel:
    """Test Document model validation"""

    def test_create_valid_document(self):
        doc = Document(
            doc_id="test-123",
            source="test",
            source_id="TEST-001",
            title="Test Document",
            body="This is test content",
            content_type="text/plain",
        )
        assert doc.doc_id == "test-123"
        assert doc.source == "test"
        assert doc.language == "en"  # default
        assert "all-employees" in doc.acl_allow

    def test_document_with_custom_acl(self):
        doc = Document(
            doc_id="test-123",
            source="test",
            source_id="TEST-001",
            title="Test",
            body="Content",
            content_type="text/plain",
            acl_allow=["admins", "managers"],
            acl_deny=["contractors"],
        )
        assert doc.acl_allow == ["admins", "managers"]
        assert doc.acl_deny == ["contractors"]

    def test_document_serialization(self):
        doc = Document(
            doc_id="test-123",
            source="test",
            source_id="TEST-001",
            title="Test",
            body="Content",
            content_type="text/plain",
        )
        doc_dict = doc.model_dump()
        assert isinstance(doc_dict, dict)
        assert doc_dict["doc_id"] == "test-123"


class TestDocumentChunkModel:
    """Test DocumentChunk model"""

    def test_create_chunk(self):
        chunk = DocumentChunk(
            chunk_id="test-123-0",
            doc_id="test-123",
            chunk_idx=0,
            text="This is a chunk of text",
            source="test",
            title="Test Document",
            content_type="text/plain",
        )
        assert chunk.chunk_id == "test-123-0"
        assert chunk.chunk_idx == 0
        assert chunk.embedding is None

    def test_chunk_with_embedding(self):
        embedding = [0.1] * 1024  # Mock embedding
        chunk = DocumentChunk(
            chunk_id="test-123-0",
            doc_id="test-123",
            chunk_idx=0,
            text="Text",
            source="test",
            title="Test",
            content_type="text/plain",
            embedding=embedding,
        )
        assert len(chunk.embedding) == 1024


class TestDocumentIngestRequest:
    """Test document ingestion request validation"""

    def test_valid_ingest_request(self):
        request = DocumentIngestRequest(
            source="test",
            source_id="TEST-001",
            title="Test Document",
            content="This is test content",
        )
        assert request.source == "test"
        assert request.content_type == "text/plain"  # default

    def test_ingest_request_missing_required_field(self):
        with pytest.raises(ValidationError):
            DocumentIngestRequest(
                source="test",
                # Missing source_id
                title="Test",
                content="Content",
            )


class TestSearchRequest:
    """Test search request validation"""

    def test_valid_search_request(self):
        request = SearchRequest(query="test query")
        assert request.query == "test query"
        assert request.size == 10  # default
        assert request.use_hybrid is True  # default

    def test_search_request_with_filters(self):
        filters = SearchFilters(sources=["servicenow"], countries=["US", "UK"])
        request = SearchRequest(query="test", filters=filters, size=20)
        assert request.filters.sources == ["servicenow"]
        assert request.size == 20

    def test_search_request_empty_query_fails(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_search_request_size_validation(self):
        # Size too large
        with pytest.raises(ValidationError):
            SearchRequest(query="test", size=1000)

        # Size negative
        with pytest.raises(ValidationError):
            SearchRequest(query="test", size=-1)


class TestUserModels:
    """Test user and authentication models"""

    def test_create_user(self):
        user = User(username="testuser", email="test@example.com", groups=["users"])
        assert user.username == "testuser"
        assert user.is_active is True  # default

    def test_user_create_validation(self):
        user_create = UserCreate(
            username="testuser", email="test@example.com", password="securepassword123"
        )
        assert user_create.username == "testuser"
        assert "all-employees" in user_create.groups  # default

    def test_user_create_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", email="not-an-email", password="password123")

    def test_user_create_short_password(self):
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", email="test@example.com", password="short")

    def test_token_model(self):
        token = Token(access_token="abc123", token_type="bearer", expires_in=3600)
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"
