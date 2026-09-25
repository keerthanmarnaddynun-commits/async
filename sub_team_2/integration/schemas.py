"""
Integration Schemas Module

Defines unified Pydantic data contracts for Team 2 Incident Analysis output.
Combines structural root-cause candidates from Infrastructure Graph and
historical post-mortem runbook matches from Provenance Memory.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TracedRootCauseSchema(BaseModel):
    """Schema representing structural root-cause candidate diagnosis from Infrastructure Graph."""

    node_id: str = Field(..., description="Node ID of identified root cause candidate")
    criticality_pagerank_score: float = Field(..., description="PageRank structural criticality score")
    path_from_trigger: List[str] = Field(..., description="Sequential path from triggering service to root cause")
    candidate_score: Optional[float] = Field(None, description="Calculated candidate relevance score")
    path_cost: Optional[float] = Field(None, description="Total Dijkstra weighted path cost")


class ProvenanceMemoryMatchSchema(BaseModel):
    """Schema representing historical runbook match from Provenance Memory Store."""

    runbook_id: str = Field(..., description="Unique runbook identifier")
    historical_fix: str = Field(..., description="Actionable historical fix")
    provenance_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    prior_success_count: int = Field(..., ge=0, description="Historical prior success count")


class Team2IncidentAnalysisSchema(BaseModel):
    """Unified Team 2 output contract combining Infrastructure Graph and Provenance Memory."""

    alert_id: str = Field(..., description="Preserved unique alert identifier")
    timestamp: str = Field(..., description="Preserved ISO-8601 formatted timestamp string")
    traced_root_cause: TracedRootCauseSchema = Field(..., description="Identified structural root cause candidate")
    provenance_memory_matches: List[ProvenanceMemoryMatchSchema] = Field(
        default_factory=list, description="List of matched historical runbooks from Provenance Memory"
    )

    @field_validator("alert_id", "timestamp")
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return value.strip()
