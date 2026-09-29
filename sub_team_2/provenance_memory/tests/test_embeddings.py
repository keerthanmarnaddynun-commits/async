from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from memory.models import HistoricalRunbook
from memory.embeddings import LocalEmbeddingModel, DEFAULT_EMBEDDING_MODEL


@pytest.fixture
def sample_runbook() -> HistoricalRunbook:
    return HistoricalRunbook(
        runbook_id="RB-AUTH-001",
        title="Auth Database Fix",
        error_signature="HTTP 503 Service Unavailable",
        historical_fix="Increased database pool size.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )


@patch("memory.embeddings.SentenceTransformer")
def test_local_embedding_model_initialization(mock_st_cls):
    model = LocalEmbeddingModel()
    assert model.model_name == DEFAULT_EMBEDDING_MODEL
    assert model._model is None


@patch("memory.embeddings.SentenceTransformer")
def test_model_name_configuration(mock_st_cls):
    custom_name = "sentence-transformers/all-mpnet-base-v2"
    model = LocalEmbeddingModel(model_name=custom_name)
    assert model.model_name == custom_name

    with pytest.raises(ValueError, match="model_name must be a non-empty string"):
        LocalEmbeddingModel(model_name="")


def test_empty_text_rejected():
    model = LocalEmbeddingModel()
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        model.embed_text("   ")


def test_non_string_text_rejected():
    model = LocalEmbeddingModel()
    with pytest.raises(TypeError, match="Input text must be a string"):
        model.embed_text(12345)


@patch("memory.embeddings.SentenceTransformer")
def test_embed_text_returns_list_float(mock_st_cls):
    mock_instance = MagicMock()
    mock_instance.encode.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    mock_st_cls.return_value = mock_instance

    model = LocalEmbeddingModel()
    vec = model.embed_text("Test query")

    assert isinstance(vec, list)
    assert all(isinstance(x, float) for x in vec)
    assert vec == pytest.approx([0.1, 0.2, 0.3])


def test_construct_runbook_text_formatting(sample_runbook: HistoricalRunbook):
    model = LocalEmbeddingModel()
    text = model.construct_runbook_text(sample_runbook)

    assert "Title:" in text
    assert "Auth Database Fix" in text
    assert "Error Signature:" in text
    assert "HTTP 503 Service Unavailable" in text
    assert "Historical Fix:" in text
    assert "Increased database pool size." in text
    assert "provenance_confidence" not in text
    assert "prior_success_count" not in text
    assert "0.92" not in text


@patch("memory.embeddings.SentenceTransformer")
def test_embed_many_returns_one_vector_per_runbook(mock_st_cls, sample_runbook: HistoricalRunbook):
    mock_instance = MagicMock()
    mock_instance.encode.return_value = np.array([
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6]
    ], dtype=np.float32)
    mock_st_cls.return_value = mock_instance

    model = LocalEmbeddingModel()
    vectors = model.embed_many([sample_runbook, sample_runbook])

    assert isinstance(vectors, list)
    assert len(vectors) == 2
    assert vectors[0] == pytest.approx([0.1, 0.2, 0.3])
    assert vectors[1] == pytest.approx([0.4, 0.5, 0.6])


@patch("memory.embeddings.SentenceTransformer")
def test_embedding_vectors_non_empty(mock_st_cls, sample_runbook: HistoricalRunbook):
    mock_instance = MagicMock()
    mock_instance.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
    mock_st_cls.return_value = mock_instance

    model = LocalEmbeddingModel()
    vec = model.embed_runbook(sample_runbook)

    assert len(vec) > 0
    assert len(vec) == 384


@patch("memory.embeddings.SentenceTransformer")
def test_embedding_dimension_property(mock_st_cls):
    mock_instance = MagicMock()
    mock_instance.get_sentence_embedding_dimension.return_value = 384
    mock_st_cls.return_value = mock_instance

    model = LocalEmbeddingModel()
    assert model.embedding_dimension == 384
