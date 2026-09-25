# Sub-Team 2 Thin Integration Layer

The `integration` package provides a lightweight orchestration layer for SovereignOps Sub-Team 2. It combines structural fault localization from `infrastructure_graph` with historical post-mortem runbook matches from `provenance_memory` into a unified Team 2 incident analysis payload.

## Architecture & Integration Flow

```
                  Common Incident Alert Context
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
   Infrastructure Graph                   Provenance Memory
(Structural Fault Localization)       (Local Vector Search & Runbooks)
            |                                     |
            | traced_root_cause                   | provenance_memory_matches
            |                                     |
            +------------------+------------------+
                               |
                               v
                  Team2Orchestrator
                               |
                               v
                 Team2IncidentAnalysisSchema
```

## Dependency Direction

Strict one-way dependency rule:

```
integration  --->  infrastructure_graph
integration  --->  provenance_memory
```

Neither `infrastructure_graph` nor `provenance_memory` imports `integration`. Underlying modules remain completely unchanged and independently testable.

## Input Contract

The orchestrator accepts a standard incident alert dictionary or Pydantic model (`AlertSchema` / `MemoryQuerySchema`):

```json
{
  "alert_id": "INC-8891",
  "timestamp": "2026-09-23T19:30:00Z",
  "triggering_service": "api-gateway-01",
  "error_signature": "HTTP 503 Service Unavailable",
  "severity": "CRITICAL"
}
```

## Unified Output Contract (`Team2IncidentAnalysisSchema`)

```json
{
  "alert_id": "INC-8891",
  "timestamp": "2026-09-23T19:30:00Z",
  "traced_root_cause": {
    "node_id": "db-auth-cluster",
    "criticality_pagerank_score": 0.2496,
    "path_from_trigger": [
      "api-gateway-01",
      "auth-service",
      "db-auth-cluster"
    ],
    "candidate_score": 0.0713,
    "path_cost": 2.5
  },
  "provenance_memory_matches": [
    {
      "runbook_id": "RB-AUTH-001",
      "historical_fix": "Increased connection pool size.",
      "provenance_confidence": 0.92,
      "prior_success_count": 14
    }
  ]
}
```

## Responsibility Boundaries

- **Infrastructure Graph**: Handles topology traversal, Dijkstra path costs, PageRank criticality, and structural fault localization.
- **Provenance Memory**: Handles sentence-transformers local embeddings, PostgreSQL pgvector similarity queries, and provenance confidence updates.
- **Integration Layer**: Orchestrates execution across both modules without recreating algorithms, database queries, embedding vectors, or scoring formulas.

## PostgreSQL Environment Note

Unit tests use isolated boundary mocks for Provenance Memory retrieval when a live database is unavailable. End-to-end vector search against PostgreSQL + `pgvector` remains an environment-dependent check requiring a running PostgreSQL server instance.
