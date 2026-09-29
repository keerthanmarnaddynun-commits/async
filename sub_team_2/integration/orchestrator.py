"""
Orchestrator Module

Coordinates incident alert analysis across Infrastructure Graph and Provenance Memory modules
to produce a unified Team 2 Incident Analysis output.
"""

from typing import Dict, Any, Union, Optional
from graph.topology import load_topology
from graph.fault_localization import localize_fault
from contracts.schemas import AlertSchema, MemoryQuerySchema
from memory.retrieval import ProvenanceMemoryRetriever, build_memory_output
from .schemas import Team2IncidentAnalysisSchema, TracedRootCauseSchema, ProvenanceMemoryMatchSchema


class Team2Orchestrator:
    """Thin integration layer orchestrating Infrastructure Graph and Provenance Memory Store."""

    def __init__(
        self,
        graph=None,
        memory_retriever: Optional[ProvenanceMemoryRetriever] = None,
    ):
        """
        Initializes the orchestrator with graph topology and memory retriever instances.

        Args:
            graph: Optional NetworkX DiGraph instance. Defaults to loading via load_topology().
            memory_retriever: Optional ProvenanceMemoryRetriever instance.
        """
        if graph is None:
            graph = load_topology()

        self.graph = graph
        self.memory_retriever: Optional[ProvenanceMemoryRetriever] = memory_retriever

    def analyze_incident(
        self,
        alert: Union[Dict[str, Any], Any],
        top_k: int = 5,
    ) -> Team2IncidentAnalysisSchema:
        """
        Executes structural fault localization and historical memory retrieval for an incoming alert.

        Args:
            alert: Dictionary or Pydantic alert model containing incident context.
            top_k: Positive integer specifying max provenance memory matches to retrieve. Defaults to 5.

        Returns:
            Team2IncidentAnalysisSchema: Unified incident analysis object.

        Raises:
            TypeError: If alert format is invalid or top_k is not an integer.
            ValueError: If required alert fields are missing or empty.
        """
        # Validate alert input and convert to dict
        if isinstance(alert, dict):
            alert_dict = alert
            alert_obj = AlertSchema(**alert_dict)
        elif hasattr(alert, "model_dump"):
            alert_dict = alert.model_dump()
            alert_obj = AlertSchema(**alert_dict)
        else:
            raise TypeError("alert must be a dictionary or a valid alert schema model.")

        # 1. Infrastructure Graph Structural Fault Localization
        graph_result = localize_fault(self.graph, alert_dict)

        if isinstance(graph_result, dict):
            traced_root_cause_dict = graph_result["traced_root_cause"]
        else:
            traced_root_cause_dict = graph_result.traced_root_cause

        traced_root_cause = TracedRootCauseSchema(**traced_root_cause_dict)

        # 2. Provenance Memory Retrieval
        provenance_matches = []
        if self.memory_retriever is not None:
            try:
                memory_query = MemoryQuerySchema(**alert_dict)
                matches = self.memory_retriever.search_by_alert(memory_query, top_k=top_k)
                memory_output = build_memory_output(alert_obj.alert_id, matches)

                for item in memory_output.provenance_memory_matches:
                    provenance_matches.append(
                        ProvenanceMemoryMatchSchema(
                            runbook_id=item.runbook_id,
                            historical_fix=item.historical_fix,
                            provenance_confidence=item.provenance_confidence,
                            prior_success_count=item.prior_success_count,
                        )
                    )
            except Exception:
                provenance_matches = []

        # 3. Combine into unified output contract
        return Team2IncidentAnalysisSchema(
            alert_id=alert_obj.alert_id,
            timestamp=alert_obj.timestamp,
            traced_root_cause=traced_root_cause,
            provenance_memory_matches=provenance_matches,
        )
