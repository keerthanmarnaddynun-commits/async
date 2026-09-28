"""
Unit tests for BFS and DFS graph traversals, downstream reachability helpers, and edge-cases.
"""

import pytest
import networkx as nx

from graph.topology import load_topology
from graph.traversal import bfs_traversal, dfs_traversal, get_downstream_nodes


@pytest.fixture
def topology_graph() -> nx.DiGraph:
    """Fixture providing a fresh instance of the 8-node infrastructure topology graph."""
    return load_topology()


def test_bfs_from_api_gateway(topology_graph: nx.DiGraph):
    """Test 1: BFS traversal starting from api-gateway-01."""
    result = bfs_traversal(topology_graph, "api-gateway-01")
    assert result[0] == "api-gateway-01"
    # Level 1 nodes (auth-service, order-service, user-service in alphabetical order)
    assert result[1:4] == ["auth-service", "order-service", "user-service"]
    assert len(result) == 8


def test_dfs_from_api_gateway(topology_graph: nx.DiGraph):
    """Test 2: DFS traversal starting from api-gateway-01."""
    result = dfs_traversal(topology_graph, "api-gateway-01")
    assert result[0] == "api-gateway-01"
    # DFS goes deep into auth-service -> db-auth-cluster first
    assert result[1] == "auth-service"
    assert result[2] == "db-auth-cluster"
    assert len(result) == 8


def test_bfs_from_auth_service(topology_graph: nx.DiGraph):
    """Test 3: BFS traversal starting from auth-service."""
    result = bfs_traversal(topology_graph, "auth-service")
    assert result == ["auth-service", "db-auth-cluster"]


def test_dfs_from_auth_service(topology_graph: nx.DiGraph):
    """Test 4: DFS traversal starting from auth-service."""
    result = dfs_traversal(topology_graph, "auth-service")
    assert result == ["auth-service", "db-auth-cluster"]


def test_traversal_of_leaf_nodes(topology_graph: nx.DiGraph):
    """Test 5: Traversal starting from leaf nodes with no outgoing dependencies."""
    bfs_leaf = bfs_traversal(topology_graph, "db-auth-cluster")
    assert bfs_leaf == ["db-auth-cluster"]

    dfs_leaf = dfs_traversal(topology_graph, "external-payment-api")
    assert dfs_leaf == ["external-payment-api"]


def test_invalid_starting_node(topology_graph: nx.DiGraph):
    """Test 6: Traversal with invalid or non-existent starting node raises KeyError."""
    with pytest.raises(KeyError, match="non-existent-service"):
        bfs_traversal(topology_graph, "non-existent-service")

    with pytest.raises(KeyError, match="invalid-node"):
        dfs_traversal(topology_graph, "invalid-node")


def test_no_duplicate_nodes(topology_graph: nx.DiGraph):
    """Test 7: Ensure traversal results contain no duplicate nodes even with multiple paths."""
    bfs_res = bfs_traversal(topology_graph, "api-gateway-01")
    assert len(bfs_res) == len(set(bfs_res))

    dfs_res = dfs_traversal(topology_graph, "api-gateway-01")
    assert len(dfs_res) == len(set(dfs_res))


def test_traversal_follows_outgoing_edges_only(topology_graph: nx.DiGraph):
    """Test 8: Traversal must strictly follow outgoing dependency edges."""
    # db-auth-cluster is a dependency target, not a source of outgoing edges
    result = bfs_traversal(topology_graph, "db-auth-cluster")
    assert "auth-service" not in result
    assert "user-service" not in result
    assert result == ["db-auth-cluster"]


def test_all_reachable_nodes_visited(topology_graph: nx.DiGraph):
    """Test 9: All 8 nodes in the topology are reachable from api-gateway-01."""
    bfs_res = bfs_traversal(topology_graph, "api-gateway-01")
    dfs_res = dfs_traversal(topology_graph, "api-gateway-01")
    assert set(bfs_res) == set(topology_graph.nodes)
    assert set(dfs_res) == set(topology_graph.nodes)


def test_original_graph_remains_unchanged(topology_graph: nx.DiGraph):
    """Test 10: Traversals must not modify the original graph nodes or edges."""
    num_nodes_before = len(topology_graph.nodes)
    num_edges_before = len(topology_graph.edges)

    _ = bfs_traversal(topology_graph, "api-gateway-01")
    _ = dfs_traversal(topology_graph, "api-gateway-01")
    _ = get_downstream_nodes(topology_graph, "order-service")

    assert len(topology_graph.nodes) == num_nodes_before
    assert len(topology_graph.edges) == num_edges_before


def test_get_downstream_nodes(topology_graph: nx.DiGraph):
    """Test helper get_downstream_nodes excludes the start_node itself."""
    downstream_order = get_downstream_nodes(topology_graph, "order-service")
    assert "order-service" not in downstream_order
    assert set(downstream_order) == {
        "user-service",
        "auth-service",
        "payment-service",
        "db-orders-cluster",
        "db-auth-cluster",
        "external-payment-api",
    }
