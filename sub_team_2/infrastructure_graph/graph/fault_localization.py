"""
Fault Localization Module (Step 6: Structural Fault Localization Layer)

Responsible for:
- Implementing Dijkstra-based shortest-path analysis using edge weights.
- Computing single-pair and single-source shortest path costs and routes across the infrastructure graph.
- Validating incident alerts (Team 2 Contract A).
- Performing structural fault localization combining graph traversals, Dijkstra path costs, and PageRank criticality scores.
"""

from datetime import datetime
from typing import Any, Dict, List
import networkx as nx

from graph.traversal import get_downstream_nodes
from graph.criticality import calculate_pagerank
from contracts.schemas import AlertSchema, FaultLocalizationOutputSchema, TracedRootCauseSchema

ALLOWED_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def dijkstra_shortest_path(graph: nx.DiGraph, source: str, target: str) -> Dict[str, Any]:
    """
    Computes the shortest weighted path and total cost between source and target using Dijkstra's algorithm.

    Args:
        graph: NetworkX directed graph.
        source: Starting node ID.
        target: Destination node ID.

    Returns:
        Dict[str, Any]: Dictionary containing source, target, path (List[str]), and total_cost (float).

    Raises:
        KeyError: If source or target does not exist in the graph.
        ValueError: If target is not reachable from source.
    """
    if source not in graph:
        raise KeyError(f"Source node '{source}' does not exist in graph.")
    if target not in graph:
        raise KeyError(f"Target node '{target}' does not exist in graph.")

    try:
        path = nx.dijkstra_path(graph, source=source, target=target, weight="weight")
        total_cost = float(nx.dijkstra_path_length(graph, source=source, target=target, weight="weight"))
    except nx.NetworkXNoPath:
        raise ValueError(f"No path exists from '{source}' to '{target}'.")

    return {
        "source": source,
        "target": target,
        "path": path,
        "total_cost": total_cost,
    }


def dijkstra_all_paths(graph: nx.DiGraph, source: str) -> Dict[str, Dict[str, Any]]:
    """
    Calculates the minimum weighted distance and shortest path from source to every reachable node.

    Args:
        graph: NetworkX directed graph.
        source: Starting node ID.

    Returns:
        Dict[str, Dict[str, Any]]: Mapping of reachable target node IDs to their minimum distance and path.

    Raises:
        KeyError: If source does not exist in the graph.
    """
    if source not in graph:
        raise KeyError(f"Source node '{source}' does not exist in graph.")

    distances, paths = nx.single_source_dijkstra(graph, source=source, weight="weight")

    results: Dict[str, Dict[str, Any]] = {}
    for node_id in distances:
        results[node_id] = {
            "distance": float(distances[node_id]),
            "path": paths[node_id],
        }

    return results


def validate_alert(alert: Any) -> None:
    """
    Validates an incoming incident alert schema (Team 2 Contract A).

    Args:
        alert: Incident alert payload.

    Raises:
        ValueError: If alert is missing, not a dictionary, or missing required fields.
    """
    if alert is None:
        raise ValueError("Alert payload cannot be None.")
    if not isinstance(alert, dict):
        raise ValueError("Alert payload must be a dictionary object.")

    required_fields = ["alert_id", "timestamp", "triggering_service", "error_signature", "severity"]
    for field in required_fields:
        if field not in alert or not alert[field]:
            raise ValueError(f"Alert payload missing required field '{field}'.")

    # Validate ISO-8601 timestamp
    ts = str(alert["timestamp"])
    ts_to_parse = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
    try:
        datetime.fromisoformat(ts_to_parse)
    except ValueError:
        raise ValueError(f"Invalid ISO-8601 timestamp format: '{ts}'.")

    # Validate severity
    severity = str(alert["severity"])
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(f"Invalid severity '{severity}'. Allowed values: {ALLOWED_SEVERITIES}")

    # Validate with Pydantic model
    try:
        AlertSchema(**alert)
    except Exception as err:
        raise ValueError(f"Alert schema validation error: {err}")


def localize_fault(graph: nx.DiGraph, alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs structural fault localization for an incident alert by exploring downstream
    dependencies, evaluating PageRank criticality and Dijkstra weighted path costs, and
    selecting the top structural root-cause candidate.

    Args:
        graph: NetworkX directed graph.
        alert: Incident alert payload dictionary.

    Returns:
        Dict[str, Any]: Structured output conforming to FaultLocalizationOutputSchema.

    Raises:
        ValueError: If alert schema is invalid.
        KeyError: If triggering_service does not exist in graph.
    """
    validate_alert(alert)

    triggering_service = alert["triggering_service"]
    if triggering_service not in graph:
        raise KeyError(f"Triggering service '{triggering_service}' does not exist in graph.")

    downstream_nodes = get_downstream_nodes(graph, triggering_service)

    # Exclude triggering service from candidates unless no downstream candidates exist
    if downstream_nodes:
        candidates = downstream_nodes
    else:
        candidates = [triggering_service]

    pr_scores = calculate_pagerank(graph)

    evaluated_candidates = []
    for cand in candidates:
        if cand == triggering_service:
            path = [triggering_service]
            path_cost = 0.0
        else:
            path_res = dijkstra_shortest_path(graph, triggering_service, cand)
            path = path_res["path"]
            path_cost = path_res["total_cost"]

        pr_score = pr_scores.get(cand, 0.0)
        cand_score = pr_score / (1.0 + path_cost)

        evaluated_candidates.append(
            {
                "node_id": cand,
                "pagerank_score": pr_score,
                "path": path,
                "path_cost": path_cost,
                "candidate_score": cand_score,
            }
        )

    # Deterministic sorting: candidate_score desc, pagerank_score desc, path_cost asc, node_id asc
    evaluated_candidates.sort(
        key=lambda x: (-x["candidate_score"], -x["pagerank_score"], x["path_cost"], x["node_id"])
    )

    top_candidate = evaluated_candidates[0]

    output_model = FaultLocalizationOutputSchema(
        alert_id=alert["alert_id"],
        timestamp=alert["timestamp"],
        traced_root_cause=TracedRootCauseSchema(
            node_id=top_candidate["node_id"],
            criticality_pagerank_score=top_candidate["pagerank_score"],
            path_from_trigger=top_candidate["path"],
            candidate_score=top_candidate["candidate_score"],
            path_cost=top_candidate["path_cost"],
        ),
        candidate_score=top_candidate["candidate_score"],
        path_cost=top_candidate["path_cost"],
        triggering_service=triggering_service,
        error_signature=alert["error_signature"],
        severity=alert["severity"],
    )

    return output_model.model_dump()
