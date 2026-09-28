"""
Schemas Module

Defines Pydantic input and output data contracts for the Provenance Memory Store.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class MemoryQuerySchema(BaseModel):
    """Input contract representing incident query context."""

    alert_id: str = Field(..., description="Unique alert identifier")
    timestamp: str = Field(..., description="ISO-8601 formatted timestamp string")
    triggering_service: str = Field(..., description="Service node ID that triggered the alert")
    error_signature: str = Field(..., description="Error signature or message")
    severity: str = Field(..., description="Alert severity level")

    @field_validator("alert_id", "timestamp", "triggering_service", "error_signature", "severity")
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return value.strip()


class ProvenanceMemoryMatchSchema(BaseModel):
    """Contract model representing a matched historical runbook result."""

    runbook_id: str = Field(..., description="Unique runbook identifier")
    historical_fix: str = Field(..., description="Actionable historical fix")
    provenance_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    prior_success_count: int = Field(..., ge=0, description="Historical prior success count")

    @field_validator("runbook_id", "historical_fix")
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return value.strip()


class ProvenanceMemoryOutputSchema(BaseModel):
    """Output contract representing the complete provenance memory retrieval result."""

    alert_id: str = Field(..., description="Preserved alert identifier")
    provenance_memory_matches: List[ProvenanceMemoryMatchSchema] = Field(
        ..., description="List of matched historical runbooks"
    )

    @field_validator("alert_id")
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return value.strip()
