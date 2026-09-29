"""
Unit tests for PageRank structural criticality calculation and node ranking logic.
"""

import pytest
import networkx as nx

from graph.topology import load_topology
from graph.criticality import (
    calculate_pagerank,
    get_node_criticality,
    rank_nodes_by_criticality,
)


@pytest.fixture
def topology_graph() -> nx.DiGraph:
    """Fixture providing a fresh instance of the 8-node infrastructure topology graph."""
    return load_topology()


def test_pagerank_all_nodes_present(topology_graph: nx.DiGraph):
    """Test 1: PageRank calculation returns scores for all 8 nodes."""
    scores = calculate_pagerank(topology_graph)
    assert len(scores) == 8
    assert set(scores.keys()) == set(topology_graph.nodes)


def test_pagerank_scores_numeric(topology_graph: nx.DiGraph):
    """Test 2: All returned PageRank scores are floats."""
    scores = calculate_pagerank(topology_graph)
    for score in scores.values():
        assert isinstance(score, float)


def test_pagerank_scores_non_negative(topology_graph: nx.DiGraph):
    """Test 3: All PageRank scores are non-negative."""
    scores = calculate_pagerank(topology_graph)
    for score in scores.values():
        assert score >= 0.0


def test_pagerank_scores_sum_to_one(topology_graph: nx.DiGraph):
    """Test 4: Total sum of all PageRank scores equals 1.0 approximately."""
    scores = calculate_pagerank(topology_graph)
    assert sum(scores.values()) == pytest.approx(1.0, abs=1e-5)


def test_get_node_criticality_valid(topology_graph: nx.DiGraph):
    """Test 5: get_node_criticality retrieves correct score for valid node."""
    score = get_node_criticality(topology_graph, "db-auth-cluster")
    assert isinstance(score, float)
    assert score > 0.0


def test_get_node_criticality_invalid(topology_graph: nx.DiGraph):
    """Test 6: get_node_criticality raises KeyError for non-existent node."""
    with pytest.raises(KeyError, match="non-existent-node"):
        get_node_criticality(topology_graph, "non-existent-node")


def test_rank_nodes_by_criticality_returns_all(topology_graph: nx.DiGraph):
    """Test 7: rank_nodes_by_criticality returns all 8 nodes."""
    ranked = rank_nodes_by_criticality(topology_graph)
    assert len(ranked) == 8
    node_ids = {item["node_id"] for item in ranked}
    assert node_ids == set(topology_graph.nodes)


def test_rank_nodes_by_criticality_sorted_descending(topology_graph: nx.DiGraph):
    """Test 8: Ranking list is sorted descending by PageRank score."""
    ranked = rank_nodes_by_criticality(topology_graph)
    scores = [item["pagerank_score"] for item in ranked]
    assert scores == sorted(scores, reverse=True)


def test_base_score_remains_unchanged(topology_graph: nx.DiGraph):
    """Test 9: Manual business base_score in graph node attributes remains unchanged."""
    original_base_score = topology_graph.nodes["api-gateway-01"]["criticality"]["base_score"]
    ranked = rank_nodes_by_criticality(topology_graph)

    gw_item = next(item for item in ranked if item["node_id"] == "api-gateway-01")
    assert gw_item["base_score"] == original_base_score
    # PageRank score must be separate and not overwrite base_score
    assert gw_item["pagerank_score"] != gw_item["base_score"]
    assert topology_graph.nodes["api-gateway-01"]["criticality"]["base_score"] == original_base_score


def test_criticality_tier_remains_unchanged(topology_graph: nx.DiGraph):
    """Test 10: Manual business tier in graph node attributes remains unchanged."""
    original_tier = topology_graph.nodes["db-auth-cluster"]["criticality"]["tier"]
    ranked = rank_nodes_by_criticality(topology_graph)

    db_item = next(item for item in ranked if item["node_id"] == "db-auth-cluster")
    assert db_item["tier"] == original_tier
    assert topology_graph.nodes["db-auth-cluster"]["criticality"]["tier"] == original_tier


def test_original_graph_not_modified_by_pagerank(topology_graph: nx.DiGraph):
    """Test 11: PageRank operations do not modify nodes or edges in original graph."""
    nodes_before = list(topology_graph.nodes)
    edges_before = list(topology_graph.edges)

    _ = calculate_pagerank(topology_graph)
    _ = rank_nodes_by_criticality(topology_graph)

    assert list(topology_graph.nodes) == nodes_before
    assert list(topology_graph.edges) == edges_before
