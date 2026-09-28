"""
Topology Module

Responsible for loading the SovereignOps IT infrastructure dependency graph from JSON,
validating node/edge structures, constructing NetworkX directed graphs (nx.DiGraph),
and providing helper queries for node attributes, outgoing dependencies, and incoming dependencies.
"""

from pathlib import Path
import json
from typing import Any, Dict, List, Union
import networkx as nx

DEFAULT_TOPOLOGY_PATH = Path(__file__).resolve().parent.parent / "data" / "topology.json"
ALLOWED_NODE_TYPES = {"gateway", "microservice", "database", "external_api"}


def validate_topology(data: Dict[str, Any]) -> None:
    """
    Validates the structure of the topology JSON data.

    Raises:
        ValueError: If required keys/fields are missing or invalid node references exist.
    """
    if not isinstance(data, dict):
        raise ValueError("Topology dataset must be a JSON object.")

    if "nodes" not in data or not isinstance(data["nodes"], list):
        raise ValueError("Topology JSON must contain a 'nodes' list.")

    if "edges" not in data or not isinstance(data["edges"], list):
        raise ValueError("Topology JSON must contain an 'edges' list.")

    node_ids = set()
    for idx, node in enumerate(data["nodes"]):
        if not isinstance(node, dict):
            raise ValueError(f"Node at index {idx} must be a dictionary.")

        node_id = node.get("node_id")
        if not node_id or not isinstance(node_id, str):
            raise ValueError(f"Node at index {idx} missing valid 'node_id'.")

        if node_id in node_ids:
            raise ValueError(f"Duplicate node_id '{node_id}' found in topology.")

        node_ids.add(node_id)

        node_type = node.get("node_type")
        if node_type not in ALLOWED_NODE_TYPES:
            raise ValueError(
                f"Node '{node_id}' has invalid node_type '{node_type}'. Allowed: {ALLOWED_NODE_TYPES}"
            )

        if "service_name" not in node or not node["service_name"]:
            raise ValueError(f"Node '{node_id}' missing required 'service_name'.")

    for idx, edge in enumerate(data["edges"]):
        if not isinstance(edge, dict):
            raise ValueError(f"Edge at index {idx} must be a dictionary.")

        source = edge.get("source")
        target = edge.get("target")

        if not source or source not in node_ids:
            raise ValueError(f"Edge at index {idx} references unknown source node '{source}'.")

        if not target or target not in node_ids:
            raise ValueError(f"Edge at index {idx} references unknown target node '{target}'.")

        if "weight" in edge and not isinstance(edge["weight"], (int, float)):
            raise ValueError(f"Edge from '{source}' to '{target}' has invalid non-numeric weight.")


def load_topology(json_path: Union[str, Path] = DEFAULT_TOPOLOGY_PATH) -> nx.DiGraph:
    """
    Loads topology JSON dataset and constructs a NetworkX directed graph (nx.DiGraph).

    Args:
        json_path: Path to topology JSON file. Defaults to DEFAULT_TOPOLOGY_PATH.

    Returns:
        nx.DiGraph: Directed graph with node and edge attributes attached.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Topology JSON file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validate_topology(data)

    graph = nx.DiGraph()

    for node in data["nodes"]:
        node_id = node["node_id"]
        attrs = {k: v for k, v in node.items() if k != "node_id"}
        graph.add_node(node_id, **attrs)

    for edge in data["edges"]:
        source = edge["source"]
        target = edge["target"]
        attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
        graph.add_edge(source, target, **attrs)

    return graph


def get_node_info(graph: nx.DiGraph, node_id: str) -> Dict[str, Any]:
    """
    Retrieves metadata dictionary for a specific node in the topology graph.

    Args:
        graph: NetworkX directed graph.
        node_id: ID of node to query.

    Returns:
        dict: Node metadata attributes including node_id.
    """
    if node_id not in graph:
        raise KeyError(f"Node '{node_id}' does not exist in graph.")

    info = {"node_id": node_id}
    info.update(graph.nodes[node_id])
    return info


def get_outgoing_dependencies(graph: nx.DiGraph, node_id: str) -> List[str]:
    """
    Retrieves list of target node IDs that node_id directly depends on (outgoing edges).

    Args:
        graph: NetworkX directed graph.
        node_id: Source node ID.

    Returns:
        list[str]: Target node IDs.
    """
    if node_id not in graph:
        raise KeyError(f"Node '{node_id}' does not exist in graph.")
    return list(graph.successors(node_id))


def get_incoming_dependencies(graph: nx.DiGraph, node_id: str) -> List[str]:
    """
    Retrieves list of source node IDs that directly depend on node_id (incoming edges).

    Args:
        graph: NetworkX directed graph.
        node_id: Target node ID.

    Returns:
        list[str]: Source node IDs.
    """
    if node_id not in graph:
        raise KeyError(f"Node '{node_id}' does not exist in graph.")
    return list(graph.predecessors(node_id))
