"""
Infrastructure Graph Demo Runner

Standalone entrypoint script demonstrating topology loading, traversals (BFS/DFS),
Weighted Path Analysis (Dijkstra), PageRank Structural Criticality, and Final Fault Localization.
"""

from graph.topology import load_topology
from graph.traversal import bfs_traversal, dfs_traversal
from graph.fault_localization import dijkstra_shortest_path, dijkstra_all_paths, localize_fault
from graph.criticality import rank_nodes_by_criticality


def run_demo():
    print("SovereignOps Infrastructure Graph")
    print("=================================")

    graph = load_topology()
    start_node = "api-gateway-01"

    print()
    print(f"Starting node: {start_node}")

    # Step 3 Traversals
    bfs_result = bfs_traversal(graph, start_node)
    print("\nBFS traversal:")
    for idx, node in enumerate(bfs_result):
        prefix = "" if idx == 0 else "-> "
        print(f"{prefix}{node}")

    dfs_result = dfs_traversal(graph, start_node)
    print("\nDFS traversal:")
    for idx, node in enumerate(dfs_result):
        prefix = "" if idx == 0 else "-> "
        print(f"{prefix}{node}")

    # Step 4 Weighted Path Analysis
    target_node = "db-auth-cluster"
    print("\nWeighted Path Analysis")
    print("======================")
    print(f"Source: {start_node}")
    print(f"Target: {target_node}")

    result = dijkstra_shortest_path(graph, start_node, target_node)
    print("\nDijkstra shortest weighted path:")
    for idx, node in enumerate(result["path"]):
        prefix = "" if idx == 0 else "-> "
        print(f"{prefix}{node}")

    print("\nTotal cost:")
    print(result["total_cost"])

    print(f"\nAll-reachable-node weighted distances from {start_node}:")
    all_paths = dijkstra_all_paths(graph, start_node)
    for node, data in sorted(all_paths.items(), key=lambda x: x[1]["distance"]):
        path_str = " -> ".join(data["path"])
        print(f"- {node}: distance = {data['distance']}, path = {path_str}")

    # Step 5 PageRank Criticality
    print("\nPageRank Structural Criticality")
    print("===============================")
    ranked_nodes = rank_nodes_by_criticality(graph)

    for idx, item in enumerate(ranked_nodes, start=1):
        print(f"{idx}. {item['node_id']}")
        print(f"   PageRank Score (Structural): {item['pagerank_score']:.4f}")
        print(f"   Service Name: {item['service_name']}")
        print(f"   Node Type: {item['node_type']}")
        print(f"   Base Criticality (Business): {item['base_score']}")
        print(f"   Tier: {item['tier']}")
        print()

    # Step 6 Structural Fault Localization
    print("==================================================")
    print("SOVEREIGNOPS -- INFRASTRUCTURE FAULT LOCALIZATION")
    print("==================================================")

    alert = {
        "alert_id": "INC-8891",
        "timestamp": "2026-09-23T19:30:00Z",
        "triggering_service": "api-gateway-01",
        "error_signature": "HTTP 503 Service Unavailable",
        "severity": "CRITICAL",
    }

    print("\nAlert:")
    print(f"  ID: {alert['alert_id']}")
    print(f"  Timestamp: {alert['timestamp']}")
    print(f"  Triggering Service: {alert['triggering_service']}")
    print(f"  Error: {alert['error_signature']}")
    print(f"  Severity: {alert['severity']}")

    localization_result = localize_fault(graph, alert)
    traced = localization_result["traced_root_cause"]
    path_str = " -> ".join(traced["path_from_trigger"])

    print("\nStructural Root-Cause Candidate:")
    print(f"  Node: {traced['node_id']}")
    print(f"  PageRank Structural Criticality: {traced['criticality_pagerank_score']:.4f}")
    print(f"  Path From Trigger: {path_str}")
    print(f"  Weighted Path Cost: {localization_result['path_cost']}")
    print(f"  Candidate Score: {localization_result['candidate_score']:.4f}")


if __name__ == "__main__":
    run_demo()
