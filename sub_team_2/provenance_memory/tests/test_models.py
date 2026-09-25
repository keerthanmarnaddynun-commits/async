"""
Unit tests for HistoricalRunbook data models, loader helper, and contract schemas.
"""

import pytest
from pydantic import ValidationError

from memory.models import HistoricalRunbook, RunbookMatch, load_mock_runbooks
from contracts.schemas import (
    MemoryQuerySchema,
    ProvenanceMemoryMatchSchema,
    ProvenanceMemoryOutputSchema,
)


def test_valid_historical_runbook_creation():
    """Test 1: Create a valid HistoricalRunbook model."""
    rb = HistoricalRunbook(
        runbook_id="RB-001",
        title="Database Latency Fix",
        error_signature="Connection Pool Exhausted",
        historical_fix="Increased pool size to 500.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )
    assert rb.runbook_id == "RB-001"
    assert rb.provenance_confidence == 0.92
    assert rb.prior_success_count == 14


def test_empty_runbook_id_rejected():
    """Test 2: Empty or whitespace runbook_id is rejected."""
    with pytest.raises(ValidationError, match="runbook_id"):
        HistoricalRunbook(
            runbook_id="   ",
            title="Title",
            error_signature="Err",
            historical_fix="Fix",
            provenance_confidence=0.5,
            prior_success_count=1,
        )


def test_empty_title_rejected():
    """Test 3: Empty or whitespace title is rejected."""
    with pytest.raises(ValidationError, match="title"):
        HistoricalRunbook(
            runbook_id="RB-001",
            title="",
            error_signature="Err",
            historical_fix="Fix",
            provenance_confidence=0.5,
            prior_success_count=1,
        )


def test_empty_error_signature_rejected():
    """Test 4: Empty or whitespace error_signature is rejected."""
    with pytest.raises(ValidationError, match="error_signature"):
        HistoricalRunbook(
            runbook_id="RB-001",
            title="Title",
            error_signature="",
            historical_fix="Fix",
            provenance_confidence=0.5,
            prior_success_count=1,
        )


def test_empty_historical_fix_rejected():
    """Test 5: Empty or whitespace historical_fix is rejected."""
    with pytest.raises(ValidationError, match="historical_fix"):
        HistoricalRunbook(
            runbook_id="RB-001",
            title="Title",
            error_signature="Err",
            historical_fix="   ",
            provenance_confidence=0.5,
            prior_success_count=1,
        )


def test_confidence_below_zero_rejected():
    """Test 6: Provenance confidence below 0.0 is rejected."""
    with pytest.raises(ValidationError):
        HistoricalRunbook(
            runbook_id="RB-001",
            title="Title",
            error_signature="Err",
            historical_fix="Fix",
            provenance_confidence=-0.1,
            prior_success_count=1,
        )


def test_confidence_above_one_rejected():
    """Test 7: Provenance confidence above 1.0 is rejected."""
    with pytest.raises(ValidationError):
        HistoricalRunbook(
            runbook_id="RB-001",
            title="Title",
            error_signature="Err",
            historical_fix="Fix",
            provenance_confidence=1.05,
            prior_success_count=1,
        )


def test_negative_success_count_rejected():
    """Test 8: Negative prior_success_count is rejected."""
    with pytest.raises(ValidationError):
        HistoricalRunbook(
            runbook_id="RB-001",
            title="Title",
            error_signature="Err",
            historical_fix="Fix",
            provenance_confidence=0.8,
            prior_success_count=-5,
        )


def test_valid_runbook_match_creation():
    """Test 9: Create a valid RunbookMatch model."""
    match = RunbookMatch(
        runbook_id="RB-001",
        historical_fix="Restarted database primary node.",
        provenance_confidence=0.90,
        prior_success_count=10,
    )
    assert match.runbook_id == "RB-001"
    assert match.provenance_confidence == 0.90


def test_valid_memory_query_schema():
    """Test 10: Create a valid MemoryQuerySchema contract object."""
    query = MemoryQuerySchema(
        alert_id="INC-8891",
        timestamp="2026-09-23T19:30:00Z",
        triggering_service="api-gateway-01",
        error_signature="HTTP 503 Service Unavailable",
        severity="CRITICAL",
    )
    assert query.alert_id == "INC-8891"
    assert query.triggering_service == "api-gateway-01"


def test_valid_provenance_memory_match_schema():
    """Test 11: Create a valid ProvenanceMemoryMatchSchema object."""
    schema = ProvenanceMemoryMatchSchema(
        runbook_id="RB-AUTH-001",
        historical_fix="Increased pool size.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )
    assert schema.runbook_id == "RB-AUTH-001"


def test_invalid_match_schema_confidence():
    """Test 12: ProvenanceMemoryMatchSchema rejects invalid confidence."""
    with pytest.raises(ValidationError):
        ProvenanceMemoryMatchSchema(
            runbook_id="RB-001",
            historical_fix="Fix",
            provenance_confidence=1.5,
            prior_success_count=2,
        )


def test_invalid_match_schema_success_count():
    """Test 13: ProvenanceMemoryMatchSchema rejects negative success count."""
    with pytest.raises(ValidationError):
        ProvenanceMemoryMatchSchema(
            runbook_id="RB-001",
            historical_fix="Fix",
            provenance_confidence=0.5,
            prior_success_count=-1,
        )


def test_valid_provenance_memory_output_schema():
    """Test 14: Create a valid ProvenanceMemoryOutputSchema contract object."""
    match = ProvenanceMemoryMatchSchema(
        runbook_id="RB-AUTH-001",
        historical_fix="Increased pool size.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )
    output = ProvenanceMemoryOutputSchema(
        alert_id="INC-8891",
        provenance_memory_matches=[match],
    )
    assert output.alert_id == "INC-8891"
    assert len(output.provenance_memory_matches) == 1


def test_load_mock_runbooks_success():
    """Test 15: Helper load_mock_runbooks successfully loads all 4 runbooks from dataset."""
    runbooks = load_mock_runbooks()
    assert len(runbooks) == 4
    assert all(isinstance(rb, HistoricalRunbook) for rb in runbooks)
    assert runbooks[0].runbook_id == "RB-AUTH-001"
    assert runbooks[1].runbook_id == "RB-PAY-002"
    assert runbooks[2].runbook_id == "RB-ORD-003"
    assert runbooks[3].runbook_id == "RB-USR-004"
