# Provenance Memory Store (Sub-Team 2)

The `provenance_memory` module manages historical post-mortem runbooks, local vector embeddings, PostgreSQL vector storage (`pgvector`), semantic similarity retrieval, and self-correcting provenance confidence feedback updates for the SovereignOps system.

## Module Structure

```
sub_team_2/provenance_memory/
├── data/
│   └── runbooks.json          # Mock dataset of historical incident runbooks
├── memory/
│   ├── __init__.py            # Package exports
│   ├── models.py              # HistoricalRunbook, RunbookMatch, RetrievedRunbookMatch models
│   ├── storage.py             # PostgresMemoryStore (PostgreSQL + pgvector operations)
│   ├── embeddings.py          # LocalEmbeddingModel (sentence-transformers local embeddings)
│   ├── retrieval.py           # ProvenanceMemoryRetriever & build_memory_output
│   └── confidence.py          # ProvenanceConfidenceManager (Outcome-based confidence updates)
├── contracts/
│   ├── __init__.py
│   └── schemas.py             # MemoryQuerySchema, ProvenanceMemoryMatchSchema, ProvenanceMemoryOutputSchema
├── tests/
│   ├── test_models.py         # Unit tests for data models & dataset loader
│   ├── test_storage.py        # Unit tests for PostgreSQL storage layer
│   ├── test_embeddings.py     # Unit tests for local embedding generation
│   ├── test_retrieval.py      # Unit tests for semantic similarity retrieval
│   ├── test_confidence.py     # Unit tests for provenance confidence updates
│   └── test_contracts.py      # Unit tests for contract schemas & build_memory_output adapter
├── demo.py                    # Local demonstration runner
├── requirements.txt           # Module dependencies (pydantic, psycopg, sentence-transformers, pytest)
└── README.md
```

## Team 2 Provenance Memory Contract

### INPUT CONTRACT: `MemoryQuerySchema`
```json
{
  "alert_id": "INC-8891",
  "timestamp": "2026-09-25T14:00:00Z",
  "triggering_service": "auth-service",
  "error_signature": "HTTP 503 Service Unavailable - Auth DB Connection Timeout",
  "severity": "CRITICAL"
}
```

### OUTPUT CONTRACT: `ProvenanceMemoryOutputSchema`
```json
{
  "alert_id": "INC-8891",
  "provenance_memory_matches": [
    {
      "runbook_id": "RB-204",
      "historical_fix": "Restart pgbouncer daemon and flush auth cache.",
      "provenance_confidence": 0.94,
      "prior_success_count": 12
    }
  ]
}
```

> **Note**: Infrastructure Graph data (such as `traced_root_cause`, PageRank scores, graph paths, or candidate node rankings) is **NOT** part of this module's output contract.

## Architectural Principles & Storage Design

1. **Local Embeddings**: Vector embeddings are generated 100% locally using `sentence-transformers` (default model: `sentence-transformers/all-MiniLM-L6-v2`, producing 384-dimensional vectors). No remote APIs or cloud inference services are used.
2. **Semantic Text Construction**: Embeddings encode semantic incident representations concatenated from:
   - `Title:`
   - `Error Signature:`
   - `Historical Fix:`
3. **Separation of Concerns**:
   - Metadata signals (`provenance_confidence`, `prior_success_count`) remain distinct and are NOT included in semantic vector embeddings.
   - Vector generation (`embeddings.py`), database execution (`storage.py`), retrieval orchestration (`retrieval.py`), and feedback processing (`confidence.py`) are strictly decoupled.
4. **Vector Search & Similarity Metric**:
   - Vector storage and similarity queries are executed locally via PostgreSQL + `pgvector`.
   - Distance metric: Cosine distance (`<=>`).
   - Similarity calculation: `similarity_score = 1 - cosine_distance`.
   - Range: Similarity scores range between `-1.0` and `1.0`.
5. **Retrieval Mechanics**:
   - `search(query_text, top_k)` generates query vector and retrieves top-k matches using parameterized SQL.
   - `search_by_alert(alert, top_k)` extracts `alert.error_signature` as the semantic query context (`Error Signature:\n<error_signature>`).
   - Runbooks with `NULL` embeddings are safely ignored during vector search (`WHERE embedding IS NOT NULL`).
   - Ties in similarity scores are broken deterministically by alphabetical `runbook_id ASC`.

## Provenance Confidence & Feedback Mechanics

1. **Provenance Confidence**: A numeric confidence score between `0.0` and `1.0` representing historical trustworthiness and reliability of a runbook fix.
2. **Prior Success Count**: An integer counter ($\ge 0$) tracking total historical successful executions of a resolution.
3. **Deterministic Update Rules**:
   - **SUCCESS Outcome**:
     - $\text{new\_confidence} = \min(1.0, \text{current\_confidence} + 0.05)$
     - $\text{new\_success\_count} = \text{prior\_success\_count} + 1$
   - **FAILURE Outcome**:
     - $\text{new\_confidence} = \max(0.0, \text{current\_confidence} - 0.10)$
     - $\text{new\_success\_count} = \text{prior\_success\_count}$ *(Success count represents cumulative successful resolutions and is never decremented on failure)*.
4. **Persistence Isolation**: `PostgresMemoryStore.update_provenance()` updates only `provenance_confidence` and `prior_success_count` columns using parameterized SQL without modifying `embedding`, `title`, `error_signature`, or `historical_fix`.

## Running Tests

Run the complete deterministic test suite (which uses mocked embedding models and mocked PostgreSQL connections):

```bash
python -m pytest tests/
```

## Running Demo

Execute the local demonstration script:

```bash
python demo.py
```
