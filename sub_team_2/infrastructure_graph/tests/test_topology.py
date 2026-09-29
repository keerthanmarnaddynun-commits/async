"""
Unit tests for topology loading, validation, directed graph behavior, node/edge metadata, and helper functions.
"""

from pathlib import Path
import pytest
import networkx as nx

from graph.topology import (
    load_topology,
    validate_topology,
    get_node_info,
    get_outgoing_dependencies,
    get_incoming_dependencies,
    DEFAULT_TOPOLOGY_PATH,
)


def test_topology_loading_success():
    """Verify that load_topology successfully loads and returns an nx.DiGraph."""
    graph = load_topology()
    assert isinstance(graph, nx.DiGraph)


def test_expected_node_count():
    """Verify that the graph contains exactly 8 nodes."""
    graph = load_topology()
    assert len(graph.nodes) == 8


def test_expected_node_ids():
    """Verify that all expected 8 service node IDs are present in the topology graph."""
    graph = load_topology()
    expected_ids = {
        "api-gateway-01",
        "auth-service",
        "user-service",
        "payment-service",
        "order-service",
        "db-auth-cluster",
        "db-orders-cluster",
        "external-payment-api",
    }
    assert set(graph.nodes) == expected_ids


def test_expected_edge_relationships():
    """Verify key directed dependency relationships exist in the graph."""
    graph = load_topology()

    # Ingress gateway edges
    assert graph.has_edge("api-gateway-01", "auth-service")
    assert graph.has_edge("api-gateway-01", "user-service")
    assert graph.has_edge("api-gateway-01", "order-service")

    # Service to DB/External API edges
    assert graph.has_edge("auth-service", "db-auth-cluster")
    assert graph.has_edge("user-service", "auth-service")
    assert graph.has_edge("user-service", "db-auth-cluster")
    assert graph.has_edge("order-service", "user-service")
    assert graph.has_edge("order-service", "auth-service")
    assert graph.has_edge("order-service", "payment-service")
    assert graph.has_edge("order-service", "db-orders-cluster")
    assert graph.has_edge("payment-service", "external-payment-api")
    assert graph.has_edge("payment-service", "db-orders-cluster")


def test_directed_graph_behavior():
    """Verify that edges are strictly directed."""
    graph = load_topology()
    assert graph.is_directed() is True

    # api-gateway-01 -> auth-service exists, but reverse edge must not exist
    assert graph.has_edge("api-gateway-01", "auth-service")
    assert not graph.has_edge("auth-service", "api-gateway-01")

    # payment-service -> external-payment-api exists, but reverse does not
    assert graph.has_edge("payment-service", "external-payment-api")
    assert not graph.has_edge("external-payment-api", "payment-service")


def test_node_metadata():
    """Verify node attributes and metadata are loaded correctly."""
    graph = load_topology()

    gateway_data = graph.nodes["api-gateway-01"]
    assert gateway_data["node_type"] == "gateway"
    assert gateway_data["service_name"] == "API Gateway 01"
    assert "criticality" in gateway_data
    assert gateway_data["criticality"]["tier"] == 1

    db_auth_data = graph.nodes["db-auth-cluster"]
    assert db_auth_data["node_type"] == "database"
    assert db_auth_data["service_name"] == "Auth Database Cluster"

    ext_api_data = graph.nodes["external-payment-api"]
    assert ext_api_data["node_type"] == "external_api"


def test_edge_metadata():
    """Verify edge attributes (dependency_type and weight) are attached correctly."""
    graph = load_topology()

    edge_gw_auth = graph.edges["api-gateway-01", "auth-service"]
    assert edge_gw_auth["dependency_type"] == "http_call"
    assert edge_gw_auth["weight"] == 1.0

    edge_pay_ext = graph.edges["payment-service", "external-payment-api"]
    assert edge_pay_ext["dependency_type"] == "external_http"
    assert edge_pay_ext["weight"] == 3.5


def test_helper_get_node_info():
    """Verify get_node_info retrieves complete node metadata including node_id."""
    graph = load_topology()
    info = get_node_info(graph, "payment-service")
    assert info["node_id"] == "payment-service"
    assert info["service_name"] == "Payment Service"
    assert info["node_type"] == "microservice"

    with pytest.raises(KeyError):
        get_node_info(graph, "non-existent-node")


def test_helper_outgoing_and_incoming_dependencies():
    """Verify outgoing (successors) and incoming (predecessors) dependency helpers."""
    graph = load_topology()

    outgoing_gw = get_outgoing_dependencies(graph, "api-gateway-01")
    assert set(outgoing_gw) == {"auth-service", "user-service", "order-service"}

    incoming_db_auth = get_incoming_dependencies(graph, "db-auth-cluster")
    assert set(incoming_db_auth) == {"auth-service", "user-service"}

    incoming_ext = get_incoming_dependencies(graph, "external-payment-api")
    assert set(incoming_ext) == {"payment-service"}

    with pytest.raises(KeyError):
        get_outgoing_dependencies(graph, "invalid-node")

    with pytest.raises(KeyError):
        get_incoming_dependencies(graph, "invalid-node")


def test_topology_validation_errors():
    """Verify validate_topology raises ValueError for corrupted inputs."""
    invalid_node_type = {
        "nodes": [
            {"node_id": "n1", "service_name": "S1", "node_type": "invalid_type"}
        ],
        "edges": []
    }
    with pytest.raises(ValueError, match="invalid node_type"):
        validate_topology(invalid_node_type)

    unknown_edge_target = {
        "nodes": [
            {"node_id": "n1", "service_name": "S1", "node_type": "microservice"}
        ],
        "edges": [
            {"source": "n1", "target": "n2", "dependency_type": "http"}
        ]
    }
    with pytest.raises(ValueError, match="unknown target node"):
        validate_topology(unknown_edge_target)
