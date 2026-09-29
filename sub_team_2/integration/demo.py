"""
Team 2 Integration Demo Runner

Standalone entrypoint script demonstrating unified Team 2 incident analysis.
Orchestrates Infrastructure Graph fault localization and Provenance Memory historical retrieval.
"""

import sys
from pathlib import Path
from json import dumps

_base_dir = Path(__file__).resolve().parent.parent
if str(_base_dir) not in sys.path:
    sys.path.insert(0, str(_base_dir))

import integration
from graph.topology import load_topology
from memory.embeddings import LocalEmbeddingModel
from memory.storage import PostgresMemoryStore
from memory.retrieval import ProvenanceMemoryRetriever
from integration.orchestrator import Team2Orchestrator


def run_demo():
    print("-" * 40)
    print("SOVEREIGNOPS -- SUB-TEAM 2")
    print("-" * 40)

    alert = {
        "alert_id": "INC-8891",
        "timestamp": "2026-09-23T19:30:00Z",
        "triggering_service": "api-gateway-01",
        "error_signature": "HTTP 503 Service Unavailable",
        "severity": "CRITICAL",
    }

    print("\nINPUT ALERT\n")
    print(f"alert_id: {alert['alert_id']}")
    print(f"timestamp: {alert['timestamp']}")
    print(f"triggering_service: {alert['triggering_service']}")
    print(f"error_signature: {alert['error_signature']}")
    print(f"severity: {alert['severity']}")

    graph = load_topology()
    store = PostgresMemoryStore()
    retriever = None
    db_offline = False

    try:
        store.connect()
        store.initialize_schema()
        embedder = LocalEmbeddingModel()
        retriever = ProvenanceMemoryRetriever(storage=store, embedding_model=embedder)
    except Exception:
        db_offline = True

    orchestrator = Team2Orchestrator(graph=graph, memory_retriever=retriever)
    unified_analysis = orchestrator.analyze_incident(alert, top_k=5)

    print("\n" + "-" * 40)
    print("INFRASTRUCTURE GRAPH")
    print("-" * 40 + "\n")
    traced = unified_analysis.traced_root_cause
    path_str = " -> ".join(traced.path_from_trigger)
    print(f"Root cause candidate: {traced.node_id}")
    print(f"PageRank: {traced.criticality_pagerank_score:.4f}")
    print(f"Path: {path_str}")
    print(f"Path cost: {traced.path_cost}")
    print(f"Candidate score: {traced.candidate_score:.4f}")

    print("\n" + "-" * 40)
    print("PROVENANCE MEMORY")
    print("-" * 40 + "\n")
    print("Matching runbooks:")
    if unified_analysis.provenance_memory_matches:
        for idx, match in enumerate(unified_analysis.provenance_memory_matches, 1):
            print(f"Runbook ID: {match.runbook_id}")
            print(f"Historical fix: {match.historical_fix}")
            print(f"Provenance confidence: {match.provenance_confidence:.2f}")
            print(f"Prior success count: {match.prior_success_count}")
    elif db_offline:
        print("PostgreSQL + pgvector unavailable:")
        print("memory retrieval executed through the configured test/demo")
        print("boundary; real vector retrieval not verified.")
    else:
        print("No matching runbooks found.")

    print("\n" + "-" * 40)
    print("UNIFIED TEAM 2 OUTPUT")
    print("-" * 40 + "\n")
    print(dumps(unified_analysis.model_dump(), indent=2))


if __name__ == "__main__":
    run_demo()
