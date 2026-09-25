"""
Confidence Module

Responsible for provenance confidence scoring, historical prior success count tracking,
and outcome-based feedback updates.
"""

from typing import Tuple
from pydantic import BaseModel, Field, field_validator
from .storage import PostgresMemoryStore


class ConfidenceUpdateResult(BaseModel):
    """Result model representing the before-and-after state of a provenance confidence update."""

    runbook_id: str = Field(..., description="Unique runbook identifier")
    previous_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence before update")
    new_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence after update")
    previous_success_count: int = Field(..., ge=0, description="Success count before update")
    new_success_count: int = Field(..., ge=0, description="Success count after update")
    outcome: str = Field(..., description="Observed outcome ('SUCCESS' or 'FAILURE')")

    @field_validator("runbook_id")
    @classmethod
    def validate_non_empty_str(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("runbook_id must be a non-empty string.")
        return value.strip()

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("outcome must be a string.")
        val_upper = value.strip().upper()
        if val_upper not in ("SUCCESS", "FAILURE"):
            raise ValueError("outcome must be either 'SUCCESS' or 'FAILURE'.")
        return val_upper


def update_provenance_confidence(
    current_confidence: float, prior_success_count: int, outcome: str
) -> Tuple[float, int]:
    """
    Computes the deterministic updated confidence score and success count given an outcome.

    - SUCCESS: new_confidence = min(1.0, current_confidence + 0.05), success_count += 1
    - FAILURE: new_confidence = max(0.0, current_confidence - 0.10), success_count unchanged

    Args:
        current_confidence: Current confidence float between 0.0 and 1.0.
        prior_success_count: Current prior success count integer >= 0.
        outcome: Outcome string ("SUCCESS" or "FAILURE").

    Returns:
        Tuple[float, int]: (new_confidence, new_success_count)

    Raises:
        TypeError: If inputs fail type validation.
        ValueError: If inputs fall outside valid ranges.
    """
    if isinstance(current_confidence, bool) or not isinstance(current_confidence, (int, float)):
        raise TypeError("current_confidence must be a float or int.")
    current_confidence = float(current_confidence)
    if current_confidence < 0.0 or current_confidence > 1.0:
        raise ValueError("current_confidence must be between 0.0 and 1.0.")

    if isinstance(prior_success_count, bool) or not isinstance(prior_success_count, int):
        raise TypeError("prior_success_count must be an integer.")
    if prior_success_count < 0:
        raise ValueError("prior_success_count must be >= 0.")

    if not isinstance(outcome, str):
        raise TypeError("outcome must be a string.")
    outcome_upper = outcome.strip().upper()
    if outcome_upper not in ("SUCCESS", "FAILURE"):
        raise ValueError("outcome must be either 'SUCCESS' or 'FAILURE'.")

    if outcome_upper == "SUCCESS":
        new_conf = min(1.0, current_confidence + 0.05)
        new_count = prior_success_count + 1
    else:  # FAILURE
        new_conf = max(0.0, current_confidence - 0.10)
        new_count = prior_success_count

    return round(new_conf, 4), new_count


class ProvenanceConfidenceManager:
    """Manages outcome feedback updates and coordinates database persistence."""

    def __init__(self, storage: PostgresMemoryStore):
        if not isinstance(storage, PostgresMemoryStore):
            raise TypeError("storage must be an instance of PostgresMemoryStore.")
        self.storage: PostgresMemoryStore = storage

    def update_outcome(self, runbook_id: str, outcome: str) -> ConfidenceUpdateResult:
        """
        Fetches runbook, calculates confidence update, persists via storage, and returns result.

        Args:
            runbook_id: Non-empty runbook identifier.
            outcome: "SUCCESS" or "FAILURE".

        Returns:
            ConfidenceUpdateResult: Object representing before and after state.

        Raises:
            ValueError: If runbook is not found or outcome is invalid.
            RuntimeError: If database update fails.
        """
        if not runbook_id or not isinstance(runbook_id, str):
            raise ValueError("runbook_id must be a non-empty string.")

        runbook = self.storage.get_runbook(runbook_id)
        if runbook is None:
            raise ValueError(f"Runbook with id '{runbook_id}' not found.")

        new_conf, new_count = update_provenance_confidence(
            current_confidence=runbook.provenance_confidence,
            prior_success_count=runbook.prior_success_count,
            outcome=outcome,
        )

        success = self.storage.update_provenance(
            runbook_id=runbook_id,
            provenance_confidence=new_conf,
            prior_success_count=new_count,
        )

        if not success:
            raise RuntimeError(f"Database update_provenance failed for runbook '{runbook_id}'.")

        return ConfidenceUpdateResult(
            runbook_id=runbook_id,
            previous_confidence=runbook.provenance_confidence,
            new_confidence=new_conf,
            previous_success_count=runbook.prior_success_count,
            new_success_count=new_count,
            outcome=outcome.strip().upper(),
        )
