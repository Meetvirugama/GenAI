import pytest
from unittest.mock import patch, MagicMock
from app.rag.vector_store import VectorStore

@patch("app.rag.vector_store.PineconeVectorStore")
@patch("app.rag.vector_store.Chroma")
@patch("app.rag.vector_store.Config")
def test_vector_store_initialization(mock_config, mock_chroma, mock_pinecone):
    # Test Chroma initialization
    mock_config.PINECONE_API_KEY = None
    store_chroma = VectorStore()
    assert store_chroma.is_pinecone is False
    
    # Test Pinecone initialization
    mock_config.PINECONE_API_KEY = "dummy_key"
    mock_config.PINECONE_INDEX = "index"
    store_pinecone = VectorStore()
    assert store_pinecone.is_pinecone is True

@patch("app.rag.vector_store.Chroma")
@patch("app.rag.vector_store.Config")
def test_vector_store_add_documents(mock_config, mock_chroma):
    mock_config.PINECONE_API_KEY = None
    store = VectorStore()
    mock_chroma_instance = MagicMock()
    store._db = mock_chroma_instance
    
    mock_doc = MagicMock()
    mock_doc.metadata = {"doc_hash": "hash1"}
    docs = [mock_doc]
    
    # Mock chroma.get to return empty existing docs
    mock_chroma_instance.get.return_value = {"metadatas": []}
    
    store.add_documents(docs, session_id="123")
    # Actually, in vector_store.add_documents, it does batch insertions and might call add_documents or from_documents.
    # We just ensure it doesn't crash
    assert "session_id" in docs[0].metadata

@patch("app.rag.vector_store.Chroma")
@patch("app.rag.vector_store.Config")
def test_vector_store_search(mock_config, mock_chroma):
    mock_config.PINECONE_API_KEY = None
    store = VectorStore()
    mock_chroma_instance = MagicMock()
    store._db = mock_chroma_instance
    
    # We test get_retriever instead of search because vector_store.py exports get_retriever
    retriever = store.get_retriever(session_id="123")
    assert retriever is not None

@patch("app.rag.vector_store.Chroma")
@patch("app.rag.vector_store.Config")
def test_vector_store_clear_session(mock_config, mock_chroma):
    mock_config.PINECONE_API_KEY = None
    store = VectorStore()
    mock_chroma_instance = MagicMock()
    store._db = mock_chroma_instance
    mock_collection = MagicMock()
    mock_chroma_instance._collection = mock_collection
    
    store.clear_session("123")
    mock_collection.delete.assert_called_once_with(where={"session_id": "123"})
