"""
Criticality Module (Step 5: PageRank Structural Criticality)

Responsible for:
- Computing PageRank scores on directed infrastructure graphs to evaluate structural dependency centrality.
- Retrieving single-node PageRank scores.
- Ranking topology nodes by structural importance while keeping base business criticality scores separate.
"""

from typing import Any, Dict, List
import networkx as nx


def calculate_pagerank(
    graph: nx.DiGraph, alpha: float = 0.85, weight: str = "weight"
) -> Dict[str, float]:
    """
    Calculates PageRank scores for all nodes in the directed infrastructure graph.

    Args:
        graph: NetworkX directed graph.
        alpha: Damping parameter for PageRank (default: 0.85).
        weight: Edge attribute key to use as weight (default: "weight").

    Returns:
        Dict[str, float]: Mapping of node_id to PageRank structural criticality score.
    """
    if len(graph) == 0:
        return {}

    scores = nx.pagerank(graph, alpha=alpha, weight=weight)
    return {node_id: float(score) for node_id, score in scores.items()}


def get_node_criticality(graph: nx.DiGraph, node_id: str) -> float:
    """
    Retrieves the PageRank structural criticality score for a specific node.

    Args:
        graph: NetworkX directed graph.
        node_id: Node ID to query.

    Returns:
        float: PageRank score.

    Raises:
        KeyError: If node_id does not exist in the graph.
    """
    if node_id not in graph:
        raise KeyError(f"Node '{node_id}' does not exist in graph.")

    scores = calculate_pagerank(graph)
    return scores[node_id]


def rank_nodes_by_criticality(graph: nx.DiGraph) -> List[Dict[str, Any]]:
    """
    Ranks topology nodes from highest PageRank structural score to lowest.
    Keeps graph-derived PageRank scores separate from manually defined business base_scores.

    Args:
        graph: NetworkX directed graph.

    Returns:
        List[Dict[str, Any]]: Ordered list of dictionaries containing node metadata,
                              pagerank_score, base_score, and tier.
    """
    scores = calculate_pagerank(graph)
    ranked = []

    for node_id, pr_score in scores.items():
        node_attrs = graph.nodes[node_id]
        crit_meta = node_attrs.get("criticality", {})
        if not isinstance(crit_meta, dict):
            crit_meta = {}

        ranked.append(
            {
                "node_id": node_id,
                "pagerank_score": pr_score,
                "service_name": node_attrs.get("service_name", node_id),
                "node_type": node_attrs.get("node_type", "unknown"),
                "base_score": crit_meta.get("base_score"),
                "tier": crit_meta.get("tier"),
            }
        )

    ranked.sort(key=lambda x: (-x["pagerank_score"], x["node_id"]))
    return ranked
