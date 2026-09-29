"""
Integration unit tests for Team2Orchestrator.
"""

from unittest.mock import MagicMock
import pytest
from memory.retrieval import ProvenanceMemoryRetriever
from memory.models import RetrievedRunbookMatch
from integration.schemas import Team2IncidentAnalysisSchema, TracedRootCauseSchema, ProvenanceMemoryMatchSchema
from integration.orchestrator import Team2Orchestrator


@pytest.fixture
def sample_alert_dict():
    return {
        "alert_id": "INC-8891",
        "timestamp": "2026-09-23T19:30:00Z",
        "triggering_service": "api-gateway-01",
        "error_signature": "HTTP 503 Service Unavailable",
        "severity": "CRITICAL",
    }


@pytest.fixture
def mock_memory_retriever():
    retriever = MagicMock(spec=ProvenanceMemoryRetriever)
    retriever.search_by_alert.return_value = [
        RetrievedRunbookMatch(
            runbook_id="RB-AUTH-001",
            historical_fix="Increased connection pool size.",
            provenance_confidence=0.92,
            prior_success_count=14,
            similarity_score=0.88,
        )
    ]
    return retriever


def test_orchestrator_valid_alert_reaches_both_modules(sample_alert_dict, mock_memory_retriever):
    orchestrator = Team2Orchestrator(memory_retriever=mock_memory_retriever)
    result = orchestrator.analyze_incident(sample_alert_dict)

    assert isinstance(result, Team2IncidentAnalysisSchema)
    assert result.alert_id == "INC-8891"
    assert result.timestamp == "2026-09-23T19:30:00Z"

    # Infrastructure Graph output verified
    assert isinstance(result.traced_root_cause, TracedRootCauseSchema)
    assert result.traced_root_cause.node_id == "db-auth-cluster"
    assert len(result.traced_root_cause.path_from_trigger) > 0

    # Provenance Memory output verified
    assert len(result.provenance_memory_matches) == 1
    assert isinstance(result.provenance_memory_matches[0], ProvenanceMemoryMatchSchema)
    assert result.provenance_memory_matches[0].runbook_id == "RB-AUTH-001"
    assert result.provenance_memory_matches[0].provenance_confidence == 0.92
    assert result.provenance_memory_matches[0].prior_success_count == 14


def test_similarity_score_not_in_final_output_dump(sample_alert_dict, mock_memory_retriever):
    orchestrator = Team2Orchestrator(memory_retriever=mock_memory_retriever)
    result = orchestrator.analyze_incident(sample_alert_dict)
    dumped = result.model_dump()

    assert "alert_id" in dumped
    assert "timestamp" in dumped
    assert "traced_root_cause" in dumped
    assert "provenance_memory_matches" in dumped

    # Field separation check
    match_dict = dumped["provenance_memory_matches"][0]
    assert "similarity_score" not in match_dict
    assert "node_id" not in match_dict
    assert "path_from_trigger" not in match_dict

    root_cause_dict = dumped["traced_root_cause"]
    assert "runbook_id" not in root_cause_dict
    assert "provenance_confidence" not in root_cause_dict


def test_empty_provenance_memory_result_handled(sample_alert_dict):
    mock_retriever = MagicMock(spec=ProvenanceMemoryRetriever)
    mock_retriever.search_by_alert.return_value = []

    orchestrator = Team2Orchestrator(memory_retriever=mock_retriever)
    result = orchestrator.analyze_incident(sample_alert_dict)

    assert result.alert_id == "INC-8891"
    assert result.traced_root_cause.node_id == "db-auth-cluster"
    assert result.provenance_memory_matches == []


def test_none_memory_retriever_handled_gracefully(sample_alert_dict):
    orchestrator = Team2Orchestrator(memory_retriever=None)
    result = orchestrator.analyze_incident(sample_alert_dict)

    assert result.alert_id == "INC-8891"
    assert result.traced_root_cause.node_id == "db-auth-cluster"
    assert result.provenance_memory_matches == []


def test_invalid_alert_format_rejected():
    orchestrator = Team2Orchestrator()
    with pytest.raises(TypeError, match="alert must be a dictionary or a valid alert schema model"):
        orchestrator.analyze_incident("invalid_alert_string")

    with pytest.raises(ValueError):
        orchestrator.analyze_incident({
            "alert_id": "",
            "timestamp": "2026-09-23T19:30:00Z",
            "triggering_service": "api-gateway-01",
            "error_signature": "HTTP 503",
            "severity": "CRITICAL"
        })
