"""
tests/test_unit_vector_store.py
================================
Comprehensive unit tests for rag/vector_store.py (VectorStore).
Target: 85%+ coverage.
"""
import os
from unittest.mock import MagicMock, patch

from langchain.schema import Document

os.environ.setdefault("GROQ_API_KEY", "fake")
os.environ.setdefault("GEMINI_API_KEY", "fake")


# ── VectorStore initialization ─────────────────────────────────────────────────

class TestVectorStoreInit:
    @patch("app.services.rag.vector_store.Config")
    def test_init_without_pinecone_uses_chroma(self, mock_config):
        """Without PINECONE_API_KEY, should use Chroma."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        store = VectorStore()
        assert store.is_pinecone is False

    @patch("app.services.rag.vector_store.Config")
    def test_init_with_pinecone_uses_pinecone(self, mock_config):
        """With both keys set, should use Pinecone."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = "some-key"
        mock_config.PINECONE_INDEX = "my-index"
        store = VectorStore()
        assert store.is_pinecone is True


# ── add_documents ──────────────────────────────────────────────────────────────

class TestAddDocuments:
    @patch("app.services.rag.vector_store.Config")
    @patch("app.services.rag.vector_store.Chroma")
    def test_add_empty_list_does_nothing(self, mock_chroma, mock_config):
        """Adding empty list should log and return early."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        store = VectorStore()
        store.add_documents([], session_id="session123")
        # No DB should have been initialized
        assert store._db is None

    @patch("app.services.rag.vector_store.Config")
    @patch("app.services.rag.vector_store.Chroma")
    def test_add_documents_sets_session_id(self, mock_chroma, mock_config):
        """Documents should have session_id added to metadata."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        mock_config.CHROMA_PERSIST_DIR = "/tmp/test_chroma"
        mock_config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"

        mock_db = MagicMock()
        mock_db.get.return_value = {"metadatas": []}
        mock_db._collection.count.return_value = 5
        mock_chroma.return_value = mock_db

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False

        docs = [
            Document(page_content="Test content", metadata={"doc_hash": "hash1"}),
        ]
        store.add_documents(docs, session_id="session-abc")
        assert docs[0].metadata["session_id"] == "session-abc"

    @patch("app.services.rag.vector_store.Config")
    def test_add_documents_skips_duplicates(self, mock_config):
        """Documents already in the store should be skipped."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None

        mock_db = MagicMock()
        # Return existing doc with same hash
        mock_db.get.return_value = {
            "metadatas": [{"doc_hash": "existing_hash", "session_id": "sess"}]
        }
        mock_db._collection.count.return_value = 1

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False

        docs = [
            Document(page_content="Existing doc", metadata={"doc_hash": "existing_hash"}),
        ]
        store.add_documents(docs, session_id="sess")
        # add_documents should not be called since all docs are duplicates
        mock_db.add_documents.assert_not_called()


# ── get_retriever ──────────────────────────────────────────────────────────────

class TestGetRetriever:
    @patch("app.services.rag.vector_store.Config")
    def test_get_retriever_no_db_returns_none(self, mock_config):
        """When DB is None (no Chroma init), should return None."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        mock_config.CHROMA_PERSIST_DIR = "/tmp/test_no_db"
        mock_config.EMBEDDING_MODEL = "test"

        store = VectorStore()
        store._db = None
        store.is_pinecone = False

        with patch("app.services.rag.vector_store.Chroma", side_effect=Exception("DB error")):
            with patch("app.services.rag.vector_store.HuggingFaceEmbeddings"):
                with patch("app.services.rag.vector_store.LocalFileStore"):
                    with patch("app.services.rag.vector_store.CacheBackedEmbeddings"):
                        result = store.get_retriever("session-abc")
        assert result is None

    @patch("app.services.rag.vector_store.Config")
    def test_get_retriever_invalid_strategy_defaults_to_dense(self, mock_config):
        """Invalid strategy string should default to DENSE."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None

        mock_db = MagicMock()
        mock_db.as_retriever.return_value = MagicMock()

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False

        with patch("app.services.rag.vector_store.RetrieverFactory.get_retriever") as mock_factory:
            mock_factory.return_value = MagicMock()
            result = store.get_retriever("session", strategy="invalid_strategy")
        assert mock_factory.called

    @patch("app.services.rag.vector_store.Config")
    def test_get_retriever_returns_retriever(self, mock_config):
        """Should return a retriever for a valid strategy."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None

        mock_db = MagicMock()
        mock_db.as_retriever.return_value = MagicMock()

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False

        with patch("app.services.rag.vector_store.RetrieverFactory.get_retriever") as mock_factory:
            expected = MagicMock()
            mock_factory.return_value = expected
            result = store.get_retriever("session", strategy="dense")
        assert result == expected


# ── is_ready ───────────────────────────────────────────────────────────────────

class TestIsReady:
    @patch("app.services.rag.vector_store.Config")
    def test_is_ready_false_when_no_db(self, mock_config):
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        store = VectorStore()
        assert store.is_ready() is False

    @patch("app.services.rag.vector_store.Config")
    def test_is_ready_true_when_pinecone(self, mock_config):
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = "key"
        mock_config.PINECONE_INDEX = "idx"
        store = VectorStore()
        store.is_pinecone = True
        assert store.is_ready() is True

    @patch("app.services.rag.vector_store.Config")
    def test_is_ready_true_when_chroma_has_docs(self, mock_config):
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        mock_db = MagicMock()
        mock_db._collection.count.return_value = 5

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False
        assert store.is_ready() is True

    @patch("app.services.rag.vector_store.Config")
    def test_is_ready_false_when_empty_chroma(self, mock_config):
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        mock_db = MagicMock()
        mock_db._collection.count.return_value = 0

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False
        assert store.is_ready() is False

    @patch("app.services.rag.vector_store.Config")
    def test_is_ready_exception_returns_false(self, mock_config):
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None
        mock_config.PINECONE_INDEX = None
        mock_db = MagicMock()
        mock_db._collection.count.side_effect = Exception("DB error")

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False
        assert store.is_ready() is False


# ── clear_session ──────────────────────────────────────────────────────────────

class TestClearSession:
    @patch("app.services.rag.vector_store.Config")
    def test_clear_session_chroma(self, mock_config):
        """Should call _collection.delete on Chroma."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None

        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db._collection = mock_collection

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False

        store.clear_session("session-123")
        mock_collection.delete.assert_called_once_with(where={"session_id": "session-123"})

    @patch("app.services.rag.vector_store.Config")
    def test_clear_session_pinecone(self, mock_config):
        """Should call delete with filter on Pinecone."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = "key"
        mock_config.PINECONE_INDEX = "idx"

        mock_db = MagicMock()
        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = True

        store.clear_session("session-456")
        mock_db.delete.assert_called_once_with(filter={"session_id": "session-456"})

    @patch("app.services.rag.vector_store.Config")
    def test_clear_session_exception_handled(self, mock_config):
        """Exceptions during clear should be caught and logged."""
        from app.services.rag.vector_store import VectorStore
        mock_config.PINECONE_API_KEY = None

        mock_db = MagicMock()
        mock_db._collection.delete.side_effect = Exception("DB error")

        store = VectorStore()
        store._db = mock_db
        store.is_pinecone = False

        # Should not raise
        store.clear_session("session-error")
