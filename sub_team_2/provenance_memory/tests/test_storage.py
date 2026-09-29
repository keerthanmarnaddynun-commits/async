"""
Unit tests for PostgreSQL storage layer (PostgresMemoryStore).
"""

from unittest.mock import MagicMock, patch
import pytest
from memory.models import HistoricalRunbook, RetrievedRunbookMatch
from memory.storage import PostgresMemoryStore


@pytest.fixture
def sample_runbook() -> HistoricalRunbook:
    return HistoricalRunbook(
        runbook_id="RB-AUTH-001",
        title="Auth DB Fix",
        error_signature="Auth DB Connection Timeout",
        historical_fix="Increased connection pool size.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )


def test_storage_initialization():
    store = PostgresMemoryStore("postgresql://user:pass@localhost:5432/testdb")
    assert store.connection_string == "postgresql://user:pass@localhost:5432/testdb"
    assert store.connection is None

    with pytest.raises(ValueError, match="Connection string must be a non-empty string."):
        PostgresMemoryStore("")


@patch("memory.storage.psycopg.connect")
def test_schema_initialization(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    store.initialize_schema()

    assert mock_cursor.execute.call_count == 2
    calls = mock_cursor.execute.call_args_list
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in calls[0][0][0]
    assert "CREATE TABLE IF NOT EXISTS historical_runbooks" in calls[1][0][0]
    mock_conn.commit.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_runbook_insertion(mock_connect, sample_runbook: HistoricalRunbook):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    store.insert_runbook(sample_runbook)

    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_parameterized_sql_usage(mock_connect, sample_runbook: HistoricalRunbook):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    store.insert_runbook(sample_runbook)

    args = mock_cursor.execute.call_args[0]
    sql_query, params = args[0], args[1]

    assert "%s" in sql_query
    assert "INSERT INTO historical_runbooks" in sql_query
    assert params == (
        "RB-AUTH-001",
        "Auth DB Fix",
        "Auth DB Connection Timeout",
        "Increased connection pool size.",
        0.92,
        14,
    )


@patch("memory.storage.psycopg.connect")
def test_get_runbook_success(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (
        "RB-AUTH-001",
        "Auth DB Fix",
        "Auth DB Timeout",
        "Fix applied.",
        0.92,
        14,
    )
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    result = store.get_runbook("RB-AUTH-001")

    assert isinstance(result, HistoricalRunbook)
    assert result.runbook_id == "RB-AUTH-001"
    assert result.provenance_confidence == 0.92


@patch("memory.storage.psycopg.connect")
def test_get_runbook_not_found(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    result = store.get_runbook("NON-EXISTENT")
    assert result is None


@patch("memory.storage.psycopg.connect")
def test_list_runbooks(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("RB-AUTH-001", "Auth DB Fix", "Auth Timeout", "Fix 1", 0.92, 14),
        ("RB-PAY-002", "Payment Gateway Fix", "Pay Timeout", "Fix 2", 0.88, 9),
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    results = store.list_runbooks()

    assert len(results) == 2
    assert all(isinstance(item, HistoricalRunbook) for item in results)


@patch("memory.storage.psycopg.connect")
def test_deterministic_list_ordering(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    _ = store.list_runbooks()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "ORDER BY runbook_id ASC" in sql_query


@patch("memory.storage.psycopg.connect")
def test_delete_runbook(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    deleted = store.delete_runbook("RB-AUTH-001")
    assert deleted is True

    mock_cursor.rowcount = 0
    not_deleted = store.delete_runbook("RB-UNKNOWN")
    assert not_deleted is False


@patch("memory.storage.psycopg.connect")
def test_rollback_on_database_failure(mock_connect, sample_runbook: HistoricalRunbook):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("DB Connection Error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    with pytest.raises(RuntimeError, match="Database insert failed"):
        store.insert_runbook(sample_runbook)

    mock_conn.rollback.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_connection_cleanup(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    store.connect()
    store.close()
    mock_conn.close.assert_called_once()
    assert store.connection is None


def test_invalid_database_operation_produces_error():
    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    with pytest.raises(ValueError, match="Input must be a valid HistoricalRunbook"):
        store.insert_runbook({"runbook_id": "invalid"})

    with pytest.raises(ValueError, match="runbook_id must be a non-empty string"):
        store.get_runbook("")

    with pytest.raises(ValueError, match="runbook_id must be a non-empty string"):
        store.delete_runbook("")


def test_invalid_embedding_rejected_by_update_embedding():
    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    with pytest.raises(ValueError, match="Embedding must be a non-empty list"):
        store.update_embedding("RB-AUTH-001", [])

    with pytest.raises(ValueError, match="All elements in embedding must be convertible to float"):
        store.update_embedding("RB-AUTH-001", ["invalid_number"])


@patch("memory.storage.psycopg.connect")
def test_update_embedding_parameterized_sql(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    success = store.update_embedding("RB-AUTH-001", [0.1, 0.2, 0.3])

    assert success is True
    mock_cursor.execute.assert_called_once()
    args = mock_cursor.execute.call_args[0]
    sql_query, params = args[0], args[1]

    assert "UPDATE historical_runbooks SET embedding = %s::vector" in sql_query
    assert params == ("[0.1,0.2,0.3]", "RB-AUTH-001")
    mock_conn.commit.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_update_embedding_rollback_on_failure(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("DB Error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    with pytest.raises(RuntimeError, match="Database update_embedding failed"):
        store.update_embedding("RB-AUTH-001", [0.1, 0.2])

    mock_conn.rollback.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_search_similar_parameterized_sql(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("RB-AUTH-001", "Increase pool size.", 0.92, 14, 0.85),
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    results = store.search_similar([0.1, 0.2, 0.3], top_k=3)

    assert len(results) == 1
    assert isinstance(results[0], RetrievedRunbookMatch)
    assert results[0].runbook_id == "RB-AUTH-001"
    assert results[0].similarity_score == 0.85

    mock_cursor.execute.assert_called_once()
    sql_query, params = mock_cursor.execute.call_args[0]
    assert "WHERE embedding IS NOT NULL" in sql_query
    assert "ORDER BY embedding <=> %s::vector ASC, runbook_id ASC" in sql_query
    assert params == ("[0.1,0.2,0.3]", "[0.1,0.2,0.3]", 3)


def test_search_similar_input_validation():
    store = PostgresMemoryStore("postgresql://localhost:5432/db")

    with pytest.raises(TypeError, match="top_k must be an integer"):
        store.search_similar([0.1, 0.2], top_k="invalid")

    with pytest.raises(TypeError, match="top_k must be an integer"):
        store.search_similar([0.1, 0.2], top_k=True)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        store.search_similar([0.1, 0.2], top_k=0)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        store.search_similar([0.1, 0.2], top_k=-5)

    with pytest.raises(ValueError, match="query_embedding must be a non-empty list"):
        store.search_similar([], top_k=5)

    with pytest.raises(ValueError, match="All elements in query_embedding must be convertible to float"):
        store.search_similar(["invalid"], top_k=5)


@patch("memory.storage.psycopg.connect")
def test_search_similar_rollback_on_failure(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("Search execution error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    with pytest.raises(RuntimeError, match="Database search_similar failed"):
        store.search_similar([0.1, 0.2], top_k=5)

    mock_conn.rollback.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_update_provenance_parameterized_sql(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    success = store.update_provenance("RB-AUTH-001", 0.97, 15)

    assert success is True
    mock_cursor.execute.assert_called_once()
    sql_query, params = mock_cursor.execute.call_args[0]

    assert "UPDATE historical_runbooks" in sql_query
    assert "SET provenance_confidence = %s" in sql_query
    assert "prior_success_count = %s" in sql_query
    assert "WHERE runbook_id = %s" in sql_query
    assert "embedding" not in sql_query  # Embedding untouched
    assert "historical_fix" not in sql_query  # Other fields untouched
    assert params == (0.97, 15, "RB-AUTH-001")
    mock_conn.commit.assert_called_once()


@patch("memory.storage.psycopg.connect")
def test_update_provenance_rollback_on_failure(mock_connect):
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("DB update error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    store = PostgresMemoryStore("postgresql://localhost:5432/db")
    with pytest.raises(RuntimeError, match="Database update_provenance failed"):
        store.update_provenance("RB-AUTH-001", 0.95, 10)

    mock_conn.rollback.assert_called_once()


def test_update_provenance_input_validation():
    store = PostgresMemoryStore("postgresql://localhost:5432/db")

    with pytest.raises(ValueError, match="runbook_id must be a non-empty string"):
        store.update_provenance("", 0.95, 10)

    with pytest.raises(ValueError, match="provenance_confidence must be between 0.0 and 1.0"):
        store.update_provenance("RB-AUTH-001", 1.5, 10)

    with pytest.raises(ValueError, match="provenance_confidence must be between 0.0 and 1.0"):
        store.update_provenance("RB-AUTH-001", -0.1, 10)

    with pytest.raises(ValueError, match="prior_success_count must be >= 0"):
        store.update_provenance("RB-AUTH-001", 0.95, -1)

    with pytest.raises(TypeError, match="provenance_confidence must be a float or int"):
        store.update_provenance("RB-AUTH-001", "invalid", 10)

    with pytest.raises(TypeError, match="prior_success_count must be an integer"):
        store.update_provenance("RB-AUTH-001", 0.95, "invalid")
