"""
Unit tests for Dijkstra-based weighted path analysis and final fault localization logic.
"""

import pytest
import networkx as nx
from pydantic import ValidationError

from graph.topology import load_topology
from graph.fault_localization import (
    dijkstra_shortest_path,
    dijkstra_all_paths,
    validate_alert,
    localize_fault,
)
from contracts.schemas import AlertSchema, FaultLocalizationOutputSchema


@pytest.fixture
def topology_graph() -> nx.DiGraph:
    """Fixture providing a fresh instance of the 8-node infrastructure topology graph."""
    return load_topology()


@pytest.fixture
def valid_alert() -> dict:
    """Fixture providing a valid incident alert dictionary."""
    return {
        "alert_id": "INC-8891",
        "timestamp": "2026-09-23T19:30:00Z",
        "triggering_service": "api-gateway-01",
        "error_signature": "HTTP 503 Service Unavailable",
        "severity": "CRITICAL",
    }


# ==================== Existing Dijkstra Tests ====================


def test_dijkstra_api_gateway_to_auth_service(topology_graph: nx.DiGraph):
    """Test 1: Dijkstra path from api-gateway-01 to auth-service."""
    res = dijkstra_shortest_path(topology_graph, "api-gateway-01", "auth-service")
    assert res["source"] == "api-gateway-01"
    assert res["target"] == "auth-service"
    assert res["path"] == ["api-gateway-01", "auth-service"]
    assert res["total_cost"] == 1.0


def test_dijkstra_api_gateway_to_db_auth_cluster(topology_graph: nx.DiGraph):
    """Test 2: Dijkstra path from api-gateway-01 to db-auth-cluster."""
    res = dijkstra_shortest_path(topology_graph, "api-gateway-01", "db-auth-cluster")
    assert res["path"] == ["api-gateway-01", "auth-service", "db-auth-cluster"]
    assert res["total_cost"] == 2.5


def test_dijkstra_api_gateway_to_external_payment_api(topology_graph: nx.DiGraph):
    """Test 3: Dijkstra path from api-gateway-01 to external-payment-api."""
    res = dijkstra_shortest_path(topology_graph, "api-gateway-01", "external-payment-api")
    assert res["path"] == [
        "api-gateway-01",
        "order-service",
        "payment-service",
        "external-payment-api",
    ]
    assert res["total_cost"] == 5.9


def test_correct_use_of_edge_weights(topology_graph: nx.DiGraph):
    """Test 4 & 5: Verify Dijkstra selects path based on cumulative weight rather than hop count."""
    res = dijkstra_shortest_path(topology_graph, "api-gateway-01", "db-auth-cluster")
    assert res["total_cost"] == 2.5
    assert res["path"] == ["api-gateway-01", "auth-service", "db-auth-cluster"]


def test_correct_path_reconstruction(topology_graph: nx.DiGraph):
    """Test 6: Path sequence accurately connects source to target."""
    res = dijkstra_shortest_path(topology_graph, "api-gateway-01", "db-orders-cluster")
    assert res["path"] == ["api-gateway-01", "order-service", "db-orders-cluster"]
    assert res["total_cost"] == 2.8


def test_invalid_source_node(topology_graph: nx.DiGraph):
    """Test 7: Invalid source node raises KeyError."""
    with pytest.raises(KeyError, match="Source node 'invalid-source'"):
        dijkstra_shortest_path(topology_graph, "invalid-source", "auth-service")


def test_invalid_target_node(topology_graph: nx.DiGraph):
    """Test 8: Invalid target node raises KeyError."""
    with pytest.raises(KeyError, match="Target node 'invalid-target'"):
        dijkstra_shortest_path(topology_graph, "api-gateway-01", "invalid-target")


def test_unreachable_target(topology_graph: nx.DiGraph):
    """Test 9: Unreachable target raises ValueError."""
    with pytest.raises(ValueError, match="No path exists"):
        dijkstra_shortest_path(topology_graph, "db-auth-cluster", "external-payment-api")


def test_directed_graph_behavior_dijkstra(topology_graph: nx.DiGraph):
    """Test 10: Traversal cannot move backwards along directed edges."""
    with pytest.raises(ValueError, match="No path exists"):
        dijkstra_shortest_path(topology_graph, "auth-service", "api-gateway-01")


def test_dijkstra_all_paths(topology_graph: nx.DiGraph):
    """Test 11: dijkstra_all_paths calculates shortest path & distance to all reachable nodes."""
    all_paths = dijkstra_all_paths(topology_graph, "api-gateway-01")
    assert len(all_paths) == 8
    assert all_paths["api-gateway-01"]["distance"] == 0.0
    assert all_paths["db-auth-cluster"]["distance"] == 2.5


# ==================== Step 6 Fault Localization & Schema Tests ====================


def test_alert_schema_validation(valid_alert: dict):
    """Test 12: AlertSchema accepts valid alert dict."""
    model = AlertSchema(**valid_alert)
    assert model.alert_id == "INC-8891"
    assert model.severity == "CRITICAL"


def test_invalid_timestamp_rejected(valid_alert: dict):
    """Test 13: Invalid ISO-8601 timestamp string is rejected."""
    bad_ts_alert = valid_alert.copy()
    bad_ts_alert["timestamp"] = "invalid-date-string"
    with pytest.raises(ValueError, match="Invalid ISO-8601 timestamp format"):
        validate_alert(bad_ts_alert)


def test_invalid_severity_rejected(valid_alert: dict):
    """Test 14: Invalid severity value is rejected."""
    bad_severity_alert = valid_alert.copy()
    bad_severity_alert["severity"] = "EXTREME_DANGER"
    with pytest.raises(ValueError, match="Invalid severity"):
        validate_alert(bad_severity_alert)


def test_fault_localization_output_schema_validation(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 15: FaultLocalizationOutputSchema validates localize_fault output."""
    res = localize_fault(topology_graph, valid_alert)
    model = FaultLocalizationOutputSchema(**res)
    assert model.alert_id == "INC-8891"
    assert model.timestamp == "2026-09-23T19:30:00Z"
    assert model.traced_root_cause.node_id == "db-auth-cluster"


def test_localize_fault_contains_timestamp(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 16: localize_fault output includes timestamp."""
    res = localize_fault(topology_graph, valid_alert)
    assert "timestamp" in res
    assert res["timestamp"] == "2026-09-23T19:30:00Z"


def test_localize_fault_preserves_alert_id(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 17: alert_id is preserved in output."""
    res = localize_fault(topology_graph, valid_alert)
    assert res["alert_id"] == "INC-8891"


def test_traced_root_cause_fields_unchanged(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 18: traced_root_cause contains node_id, criticality_pagerank_score, path_from_trigger."""
    res = localize_fault(topology_graph, valid_alert)
    traced = res["traced_root_cause"]
    assert traced["node_id"] == "db-auth-cluster"
    assert traced["criticality_pagerank_score"] == pytest.approx(0.2496, abs=1e-3)
    assert traced["path_from_trigger"] == ["api-gateway-01", "auth-service", "db-auth-cluster"]


def test_candidate_scoring_formula_unchanged(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 19: candidate_score matches PageRank / (1 + path_cost)."""
    res = localize_fault(topology_graph, valid_alert)
    traced = res["traced_root_cause"]
    expected_score = traced["criticality_pagerank_score"] / (1.0 + res["path_cost"])
    assert res["candidate_score"] == pytest.approx(expected_score)


def test_deterministic_tie_breaking(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 20: Repeatable deterministic results on repeated execution."""
    res1 = localize_fault(topology_graph, valid_alert)
    res2 = localize_fault(topology_graph, valid_alert)
    assert res1["candidate_score"] == res2["candidate_score"]
    assert res1["traced_root_cause"]["node_id"] == res2["traced_root_cause"]["node_id"]


def test_missing_alert_raises_error(topology_graph: nx.DiGraph):
    """Test 21: Missing or None alert raises ValueError."""
    with pytest.raises(ValueError, match="Alert payload cannot be None"):
        localize_fault(topology_graph, None)


def test_missing_required_field_raises_error(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 22: Alert missing required fields raises ValueError."""
    incomplete_alert = valid_alert.copy()
    del incomplete_alert["error_signature"]
    with pytest.raises(ValueError, match="missing required field 'error_signature'"):
        localize_fault(topology_graph, incomplete_alert)


def test_invalid_triggering_service_raises_error(topology_graph: nx.DiGraph, valid_alert: dict):
    """Test 23: Alert with non-existent triggering_service raises KeyError."""
    bad_service_alert = valid_alert.copy()
    bad_service_alert["triggering_service"] = "non-existent-gateway"
    with pytest.raises(KeyError, match="Triggering service 'non-existent-gateway'"):
        localize_fault(topology_graph, bad_service_alert)


def test_non_dictionary_alert_raises_error(topology_graph: nx.DiGraph):
    """Test 24: Non-dictionary alert raises ValueError."""
    with pytest.raises(ValueError, match="Alert payload must be a dictionary"):
        localize_fault(topology_graph, "INC-8891")
