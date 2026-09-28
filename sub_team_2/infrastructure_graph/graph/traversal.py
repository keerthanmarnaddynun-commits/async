"""
Traversal Module

Responsible for:
- Implementing Breadth-First Search (BFS) graph traversal on infrastructure dependency graphs.
- Implementing Depth-First Search (DFS) graph traversal on infrastructure dependency graphs.
- Providing downstream dependency reachability helpers.
"""

from collections import deque
from typing import List, Set
import networkx as nx


def bfs_traversal(graph: nx.DiGraph, start_node: str) -> List[str]:
    """
    Performs a deterministic Breadth-First Search (BFS) traversal starting from start_node,
    following outgoing dependency edges.

    Args:
        graph: NetworkX directed graph.
        start_node: Node ID to start traversal from.

    Returns:
        List[str]: Ordered list of visited node IDs in BFS order.

    Raises:
        KeyError: If start_node is not in the graph.
    """
    if start_node not in graph:
        raise KeyError(f"Starting node '{start_node}' does not exist in graph.")

    visited: Set[str] = {start_node}
    queue: deque = deque([start_node])
    traversal_order: List[str] = []

    while queue:
        current = queue.popleft()
        traversal_order.append(current)

        # Sort outgoing neighbors alphabetically for deterministic traversal order
        neighbors = sorted(graph.successors(current))
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return traversal_order


def dfs_traversal(graph: nx.DiGraph, start_node: str) -> List[str]:
    """
    Performs a deterministic Depth-First Search (DFS) traversal starting from start_node,
    following outgoing dependency edges.

    Args:
        graph: NetworkX directed graph.
        start_node: Node ID to start traversal from.

    Returns:
        List[str]: Ordered list of visited node IDs in DFS order.

    Raises:
        KeyError: If start_node is not in the graph.
    """
    if start_node not in graph:
        raise KeyError(f"Starting node '{start_node}' does not exist in graph.")

    visited: Set[str] = set()
    traversal_order: List[str] = []

    def _dfs(node: str) -> None:
        visited.add(node)
        traversal_order.append(node)

        # Sort outgoing neighbors alphabetically for deterministic traversal order
        neighbors = sorted(graph.successors(node))
        for neighbor in neighbors:
            if neighbor not in visited:
                _dfs(neighbor)

    _dfs(start_node)
    return traversal_order


def get_downstream_nodes(graph: nx.DiGraph, start_node: str) -> List[str]:
    """
    Retrieves all nodes reachable downstream from start_node (excluding start_node itself).

    Args:
        graph: NetworkX directed graph.
        start_node: Node ID to find downstream dependencies for.

    Returns:
        List[str]: List of downstream reachable node IDs.

    Raises:
        KeyError: If start_node is not in the graph.
    """
    full_traversal = bfs_traversal(graph, start_node)
    return [node for node in full_traversal if node != start_node]
