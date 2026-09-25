"""
Unit tests for confidence module (provenance confidence updates & feedback logic).
"""

from unittest.mock import MagicMock
import pytest
from memory.confidence import (
    ConfidenceUpdateResult,
    update_provenance_confidence,
    ProvenanceConfidenceManager,
)
from memory.models import HistoricalRunbook
from memory.storage import PostgresMemoryStore


def test_update_provenance_confidence_success():
    new_conf, new_count = update_provenance_confidence(
        current_confidence=0.92, prior_success_count=14, outcome="SUCCESS"
    )
    assert new_conf == 0.97
    assert new_count == 15


def test_update_provenance_confidence_failure():
    new_conf, new_count = update_provenance_confidence(
        current_confidence=0.92, prior_success_count=14, outcome="FAILURE"
    )
    assert new_conf == 0.82
    assert new_count == 14  # Success count must NOT be decremented


def test_upper_bound_enforced():
    # 0.98 + 0.05 = 1.03 -> capped at 1.0
    conf1, count1 = update_provenance_confidence(0.98, 5, "SUCCESS")
    assert conf1 == 1.0
    assert count1 == 6

    # 1.0 + 0.05 = 1.05 -> capped at 1.0
    conf2, count2 = update_provenance_confidence(1.0, 5, "SUCCESS")
    assert conf2 == 1.0
    assert count2 == 6


def test_lower_bound_enforced():
    # 0.05 - 0.10 = -0.05 -> floored at 0.0
    conf1, count1 = update_provenance_confidence(0.05, 5, "FAILURE")
    assert conf1 == 0.0
    assert count1 == 5

    # 0.0 - 0.10 = -0.10 -> floored at 0.0
    conf2, count2 = update_provenance_confidence(0.0, 5, "FAILURE")
    assert conf2 == 0.0
    assert count2 == 5


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError, match="current_confidence must be between 0.0 and 1.0"):
        update_provenance_confidence(1.5, 5, "SUCCESS")

    with pytest.raises(ValueError, match="current_confidence must be between 0.0 and 1.0"):
        update_provenance_confidence(-0.1, 5, "SUCCESS")

    with pytest.raises(TypeError, match="current_confidence must be a float or int"):
        update_provenance_confidence("0.9", 5, "SUCCESS")

    with pytest.raises(ValueError, match="prior_success_count must be >= 0"):
        update_provenance_confidence(0.5, -1, "SUCCESS")

    with pytest.raises(TypeError, match="prior_success_count must be an integer"):
        update_provenance_confidence(0.5, "five", "SUCCESS")

    with pytest.raises(ValueError, match="outcome must be either 'SUCCESS' or 'FAILURE'"):
        update_provenance_confidence(0.5, 5, "UNKNOWN")


def test_confidence_update_result_validation():
    res = ConfidenceUpdateResult(
        runbook_id="RB-AUTH-001",
        previous_confidence=0.92,
        new_confidence=0.97,
        previous_success_count=14,
        new_success_count=15,
        outcome="SUCCESS",
    )
    assert res.runbook_id == "RB-AUTH-001"
    assert res.new_confidence == 0.97
    assert res.new_success_count == 15

    with pytest.raises(ValueError, match="outcome must be either 'SUCCESS' or 'FAILURE'"):
        ConfidenceUpdateResult(
            runbook_id="RB-AUTH-001",
            previous_confidence=0.92,
            new_confidence=0.97,
            previous_success_count=14,
            new_success_count=15,
            outcome="INVALID",
        )


def test_provenance_confidence_manager_success():
    mock_storage = MagicMock(spec=PostgresMemoryStore)
    mock_storage.get_runbook.return_value = HistoricalRunbook(
        runbook_id="RB-AUTH-001",
        title="Auth Fix",
        error_signature="Auth Error",
        historical_fix="Increased pool size.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )
    mock_storage.update_provenance.return_value = True

    manager = ProvenanceConfidenceManager(storage=mock_storage)
    result = manager.update_outcome("RB-AUTH-001", "SUCCESS")

    mock_storage.get_runbook.assert_called_once_with("RB-AUTH-001")
    mock_storage.update_provenance.assert_called_once_with(
        runbook_id="RB-AUTH-001", provenance_confidence=0.97, prior_success_count=15
    )

    assert isinstance(result, ConfidenceUpdateResult)
    assert result.previous_confidence == 0.92
    assert result.new_confidence == 0.97
    assert result.previous_success_count == 14
    assert result.new_success_count == 15
    assert result.outcome == "SUCCESS"


def test_provenance_confidence_manager_failure_outcome():
    mock_storage = MagicMock(spec=PostgresMemoryStore)
    mock_storage.get_runbook.return_value = HistoricalRunbook(
        runbook_id="RB-AUTH-001",
        title="Auth Fix",
        error_signature="Auth Error",
        historical_fix="Increased pool size.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )
    mock_storage.update_provenance.return_value = True

    manager = ProvenanceConfidenceManager(storage=mock_storage)
    result = manager.update_outcome("RB-AUTH-001", "FAILURE")

    mock_storage.update_provenance.assert_called_once_with(
        runbook_id="RB-AUTH-001", provenance_confidence=0.82, prior_success_count=14
    )
    assert result.new_confidence == 0.82
    assert result.new_success_count == 14
    assert result.outcome == "FAILURE"


def test_provenance_confidence_manager_missing_runbook():
    mock_storage = MagicMock(spec=PostgresMemoryStore)
    mock_storage.get_runbook.return_value = None

    manager = ProvenanceConfidenceManager(storage=mock_storage)
    with pytest.raises(ValueError, match="Runbook with id 'NON-EXISTENT' not found"):
        manager.update_outcome("NON-EXISTENT", "SUCCESS")


def test_provenance_confidence_manager_database_update_failure():
    mock_storage = MagicMock(spec=PostgresMemoryStore)
    mock_storage.get_runbook.return_value = HistoricalRunbook(
        runbook_id="RB-AUTH-001",
        title="Auth Fix",
        error_signature="Auth Error",
        historical_fix="Fix.",
        provenance_confidence=0.92,
        prior_success_count=14,
    )
    mock_storage.update_provenance.return_value = False

    manager = ProvenanceConfidenceManager(storage=mock_storage)
    with pytest.raises(RuntimeError, match="Database update_provenance failed"):
        manager.update_outcome("RB-AUTH-001", "SUCCESS")
