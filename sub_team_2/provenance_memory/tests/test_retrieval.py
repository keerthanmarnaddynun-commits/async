"""
Unit tests for ProvenanceMemoryRetriever semantic similarity search.
"""

from unittest.mock import MagicMock
import pytest
from contracts.schemas import MemoryQuerySchema
from memory.models import RetrievedRunbookMatch
from memory.retrieval import ProvenanceMemoryRetriever
from memory.storage import PostgresMemoryStore
from memory.embeddings import LocalEmbeddingModel


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock(spec=PostgresMemoryStore)
    return storage


@pytest.fixture
def mock_embedding_model() -> MagicMock:
    model = MagicMock(spec=LocalEmbeddingModel)
    model.embed_text.return_value = [0.1, 0.2, 0.3, 0.4]
    return model


@pytest.fixture
def retriever(mock_storage: MagicMock, mock_embedding_model: MagicMock) -> ProvenanceMemoryRetriever:
    return ProvenanceMemoryRetriever(storage=mock_storage, embedding_model=mock_embedding_model)


def test_retriever_initialization_validation(mock_storage: MagicMock, mock_embedding_model: MagicMock):
    retriever = ProvenanceMemoryRetriever(mock_storage, mock_embedding_model)
    assert retriever.storage == mock_storage
    assert retriever.embedding_model == mock_embedding_model

    with pytest.raises(TypeError, match="storage must be an instance of PostgresMemoryStore"):
        ProvenanceMemoryRetriever("invalid_storage", mock_embedding_model)

    with pytest.raises(TypeError, match="embedding_model must be an instance of LocalEmbeddingModel"):
        ProvenanceMemoryRetriever(mock_storage, "invalid_model")


def test_valid_query_returns_matches(retriever: ProvenanceMemoryRetriever, mock_storage: MagicMock, mock_embedding_model: MagicMock):
    mock_storage.search_similar.return_value = [
        RetrievedRunbookMatch(
            runbook_id="RB-AUTH-001",
            historical_fix="Increase connection pool size.",
            provenance_confidence=0.92,
            prior_success_count=14,
            similarity_score=0.88,
        )
    ]

    results = retriever.search("Auth DB Connection Pool Exhaustion", top_k=5)

    mock_embedding_model.embed_text.assert_called_once_with("Auth DB Connection Pool Exhaustion")
    mock_storage.search_similar.assert_called_once_with([0.1, 0.2, 0.3, 0.4], top_k=5)

    assert len(results) == 1
    assert isinstance(results[0], RetrievedRunbookMatch)
    assert results[0].runbook_id == "RB-AUTH-001"
    assert results[0].provenance_confidence == 0.92
    assert results[0].prior_success_count == 14
    assert results[0].similarity_score == 0.88


def test_top_k_default_and_custom(retriever: ProvenanceMemoryRetriever, mock_storage: MagicMock):
    mock_storage.search_similar.return_value = []

    retriever.search("test query")
    mock_storage.search_similar.assert_called_with([0.1, 0.2, 0.3, 0.4], top_k=5)

    retriever.search("test query", top_k=1)
    mock_storage.search_similar.assert_called_with([0.1, 0.2, 0.3, 0.4], top_k=1)


def test_invalid_top_k_rejected(retriever: ProvenanceMemoryRetriever):
    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        retriever.search("valid query", top_k=0)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        retriever.search("valid query", top_k=-3)

    with pytest.raises(TypeError, match="top_k must be an integer"):
        retriever.search("valid query", top_k=True)

    with pytest.raises(TypeError, match="top_k must be an integer"):
        retriever.search("valid query", top_k="invalid")


def test_invalid_query_text_rejected(retriever: ProvenanceMemoryRetriever):
    with pytest.raises(ValueError, match="query_text must be a non-empty string"):
        retriever.search("")

    with pytest.raises(ValueError, match="query_text must be a non-empty string"):
        retriever.search("   ")

    with pytest.raises(ValueError, match="query_text must be a non-empty string"):
        retriever.search(123)


def test_empty_database_returns_empty_list(retriever: ProvenanceMemoryRetriever, mock_storage: MagicMock):
    mock_storage.search_similar.return_value = []

    results = retriever.search("Unknown error signature", top_k=5)
    assert results == []


def test_search_by_alert_valid(retriever: ProvenanceMemoryRetriever, mock_storage: MagicMock, mock_embedding_model: MagicMock):
    alert = MemoryQuerySchema(
        alert_id="ALT-100",
        timestamp="2026-09-25T14:00:00Z",
        triggering_service="auth-service",
        error_signature="HTTP 503 Service Unavailable - Auth DB Pool Exhausted",
        severity="CRITICAL",
    )

    mock_storage.search_similar.return_value = [
        RetrievedRunbookMatch(
            runbook_id="RB-AUTH-001",
            historical_fix="Increase pool size.",
            provenance_confidence=0.92,
            prior_success_count=14,
            similarity_score=0.91,
        )
    ]

    results = retriever.search_by_alert(alert, top_k=3)

    expected_query = "Error Signature:\nHTTP 503 Service Unavailable - Auth DB Pool Exhausted"
    mock_embedding_model.embed_text.assert_called_once_with(expected_query)
    mock_storage.search_similar.assert_called_once_with([0.1, 0.2, 0.3, 0.4], top_k=3)
    assert len(results) == 1
    assert results[0].runbook_id == "RB-AUTH-001"


def test_search_by_alert_invalid_alert(retriever: ProvenanceMemoryRetriever):
    with pytest.raises(TypeError, match="alert must be an instance of MemoryQuerySchema"):
        retriever.search_by_alert({"error_signature": "Auth error"})


def test_deterministic_and_tie_breaking(mock_storage: MagicMock, mock_embedding_model: MagicMock):
    # Simulated matches from database sorted by similarity score descending then runbook_id ASC
    mock_storage.search_similar.return_value = [
        RetrievedRunbookMatch(
            runbook_id="RB-AUTH-001",
            historical_fix="Fix 1",
            provenance_confidence=0.9,
            prior_success_count=10,
            similarity_score=0.85,
        ),
        RetrievedRunbookMatch(
            runbook_id="RB-ORD-003",
            historical_fix="Fix 3",
            provenance_confidence=0.8,
            prior_success_count=5,
            similarity_score=0.85,
        ),
    ]

    retriever = ProvenanceMemoryRetriever(mock_storage, mock_embedding_model)
    res1 = retriever.search("query text")
    res2 = retriever.search("query text")

    assert res1 == res2
    assert res1[0].runbook_id == "RB-AUTH-001"
    assert res1[1].runbook_id == "RB-ORD-003"
