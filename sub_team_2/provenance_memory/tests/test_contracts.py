"""
Unit tests for Team 2 Provenance Memory contract schemas and output adapter.
"""

import pytest
from contracts.schemas import (
    MemoryQuerySchema,
    ProvenanceMemoryMatchSchema,
    ProvenanceMemoryOutputSchema,
)
from memory.models import RetrievedRunbookMatch
from memory.retrieval import build_memory_output


def test_valid_provenance_memory_output_schema():
    match_item = ProvenanceMemoryMatchSchema(
        runbook_id="RB-204",
        historical_fix="Restart pgbouncer daemon and flush auth cache.",
        provenance_confidence=0.94,
        prior_success_count=12,
    )
    output = ProvenanceMemoryOutputSchema(
        alert_id="INC-8891",
        provenance_memory_matches=[match_item],
    )

    assert output.alert_id == "INC-8891"
    assert len(output.provenance_memory_matches) == 1
    assert output.provenance_memory_matches[0].runbook_id == "RB-204"
    assert output.provenance_memory_matches[0].provenance_confidence == 0.94
    assert output.provenance_memory_matches[0].prior_success_count == 12


def test_invalid_confidence_rejected():
    with pytest.raises(ValueError):
        ProvenanceMemoryMatchSchema(
            runbook_id="RB-204",
            historical_fix="Fix",
            provenance_confidence=1.5,
            prior_success_count=5,
        )

    with pytest.raises(ValueError):
        ProvenanceMemoryMatchSchema(
            runbook_id="RB-204",
            historical_fix="Fix",
            provenance_confidence=-0.1,
            prior_success_count=5,
        )


def test_invalid_success_count_rejected():
    with pytest.raises(ValueError):
        ProvenanceMemoryMatchSchema(
            runbook_id="RB-204",
            historical_fix="Fix",
            provenance_confidence=0.9,
            prior_success_count=-1,
        )


def test_empty_runbook_id_rejected():
    with pytest.raises(ValueError, match="Field 'runbook_id' must be a non-empty string"):
        ProvenanceMemoryMatchSchema(
            runbook_id="",
            historical_fix="Fix",
            provenance_confidence=0.9,
            prior_success_count=5,
        )


def test_empty_historical_fix_rejected():
    with pytest.raises(ValueError, match="Field 'historical_fix' must be a non-empty string"):
        ProvenanceMemoryMatchSchema(
            runbook_id="RB-204",
            historical_fix="   ",
            provenance_confidence=0.9,
            prior_success_count=5,
        )


def test_build_memory_output_adapter_preserves_fields():
    matches = [
        RetrievedRunbookMatch(
            runbook_id="RB-AUTH-001",
            historical_fix="Increase connection pool size.",
            provenance_confidence=0.92,
            prior_success_count=14,
            similarity_score=0.88,
        ),
        RetrievedRunbookMatch(
            runbook_id="RB-PAY-002",
            historical_fix="Increase HTTP timeout to 30s.",
            provenance_confidence=0.88,
            prior_success_count=9,
            similarity_score=0.75,
        ),
    ]

    output = build_memory_output("INC-1001", matches)

    assert isinstance(output, ProvenanceMemoryOutputSchema)
    assert output.alert_id == "INC-1001"
    assert len(output.provenance_memory_matches) == 2

    # Check first item
    assert output.provenance_memory_matches[0].runbook_id == "RB-AUTH-001"
    assert output.provenance_memory_matches[0].historical_fix == "Increase connection pool size."
    assert output.provenance_memory_matches[0].provenance_confidence == 0.92
    assert output.provenance_memory_matches[0].prior_success_count == 14

    # Check second item
    assert output.provenance_memory_matches[1].runbook_id == "RB-PAY-002"
    assert output.provenance_memory_matches[1].historical_fix == "Increase HTTP timeout to 30s."
    assert output.provenance_memory_matches[1].provenance_confidence == 0.88
    assert output.provenance_memory_matches[1].prior_success_count == 9


def test_similarity_score_does_not_leak_into_external_contract():
    matches = [
        RetrievedRunbookMatch(
            runbook_id="RB-AUTH-001",
            historical_fix="Increase pool size.",
            provenance_confidence=0.92,
            prior_success_count=14,
            similarity_score=0.88,
        )
    ]

    output = build_memory_output("INC-1001", matches)
    dumped_dict = output.model_dump()

    # External contract dump must contain alert_id and provenance_memory_matches
    assert "alert_id" in dumped_dict
    assert "provenance_memory_matches" in dumped_dict

    match_dict = dumped_dict["provenance_memory_matches"][0]
    assert "runbook_id" in match_dict
    assert "historical_fix" in match_dict
    assert "provenance_confidence" in match_dict
    assert "prior_success_count" in match_dict
    assert "similarity_score" not in match_dict  # Must NOT leak into external contract schema!


def test_build_memory_output_validation():
    with pytest.raises(ValueError, match="alert_id must be a non-empty string"):
        build_memory_output("", [])

    with pytest.raises(TypeError, match="matches must be a list or tuple"):
        build_memory_output("INC-100", "invalid_matches")

    with pytest.raises(TypeError, match="Each match must be an instance of RetrievedRunbookMatch"):
        build_memory_output("INC-100", [{"runbook_id": "RB-1"}])
