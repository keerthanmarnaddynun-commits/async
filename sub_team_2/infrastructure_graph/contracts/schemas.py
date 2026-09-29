"""
Schemas Module

Defines Pydantic models for topology nodes, edges, incident alerts, traced root-cause candidates,
and fault localization output payloads. Ensures standardized schemas for integration with
Provenance Memory Store and Team 1.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AlertSchema(BaseModel):
    alert_id: str = Field(..., description="Unique alert incident identifier")
    timestamp: str = Field(..., description="ISO-8601 formatted timestamp string")
    triggering_service: str = Field(..., description="Node ID of the service triggering the alert")
    error_signature: str = Field(..., description="Description or status code of error")
    severity: str = Field(..., description="Incident severity (CRITICAL, HIGH, MEDIUM, LOW)")


class TracedRootCauseSchema(BaseModel):
    node_id: str = Field(..., description="Node ID of identified root cause candidate")
    criticality_pagerank_score: float = Field(..., description="PageRank structural criticality score")
    path_from_trigger: List[str] = Field(..., description="Sequential path from triggering service to root cause")
    candidate_score: Optional[float] = Field(None, description="Calculated candidate relevance score")
    path_cost: Optional[float] = Field(None, description="Total Dijkstra weighted path cost")


class FaultLocalizationOutputSchema(BaseModel):
    alert_id: str = Field(..., description="Preserved incident alert ID")
    timestamp: str = Field(..., description="Preserved incident alert ISO-8601 timestamp")
    traced_root_cause: TracedRootCauseSchema = Field(..., description="Structural root-cause candidate diagnosis")
    candidate_score: Optional[float] = Field(None, description="Overall candidate score")
    path_cost: Optional[float] = Field(None, description="Path cost from trigger to candidate")
    triggering_service: Optional[str] = Field(None, description="Triggering service node ID")
    error_signature: Optional[str] = Field(None, description="Error signature description")
    severity: Optional[str] = Field(None, description="Alert severity string")
