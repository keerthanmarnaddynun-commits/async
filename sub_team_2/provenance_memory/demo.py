"""
Provenance Memory Demo Runner

Standalone entrypoint script demonstrating memory store initialization, dataset loading,
local vector embedding generation, semantic similarity retrieval via pgvector, and
provenance confidence feedback updates.
"""

from memory.models import load_mock_runbooks
from memory.embeddings import LocalEmbeddingModel
from memory.storage import PostgresMemoryStore
from memory.retrieval import ProvenanceMemoryRetriever
from memory.confidence import update_provenance_confidence, ProvenanceConfidenceManager


def run_demo():
    print("SovereignOps -- Provenance Memory Store")
    print("=======================================")

    runbooks = load_mock_runbooks()
    print(f"\nLoaded {len(runbooks)} mock runbooks from dataset:")
    for rb in runbooks:
        print(f"  - [{rb.runbook_id}] {rb.title} (Confidence: {rb.provenance_confidence}, Successes: {rb.prior_success_count})")

    print("\nLocal Embedding Generation (sentence-transformers)")
    print("---------------------------------------------------")
    sample_rb = runbooks[0]

    embedder = LocalEmbeddingModel()
    vector = embedder.embed_runbook(sample_rb)

    print(f"Runbook ID: {sample_rb.runbook_id}")
    print(f"Embedding Model: {embedder.model_name}")
    print(f"Embedding Dimension: {embedder.embedding_dimension}")
    truncated_vec = [round(x, 4) for x in vector[:5]]
    print(f"First 5 vector values: {truncated_vec}...")

    print("\nSemantic Similarity Retrieval (pgvector)")
    print("----------------------------------------")
    store = PostgresMemoryStore()

    query_text = "HTTP 503 Service Unavailable - Auth DB Connection Timeout"
    print(f"Query: \"{query_text}\"\n")

    try:
        store.connect()
        store.initialize_schema()

        print("Updating database runbook records and embeddings...")
        for rb in runbooks:
            store.insert_runbook(rb)
            rb_vec = embedder.embed_runbook(rb)
            store.update_embedding(rb.runbook_id, rb_vec)

        retriever = ProvenanceMemoryRetriever(storage=store, embedding_model=embedder)
        matches = retriever.search(query_text, top_k=5)

        print(f"Top {len(matches)} Retrieved Historical Runbook Matches:\n")
        print(f"{'Rank':<5} {'Runbook ID':<15} {'Semantic Similarity':<22} {'Provenance Confidence':<24} {'Prior Successes':<18} {'Historical Fix'}")
        print("-" * 110)

        for idx, match in enumerate(matches, 1):
            print(
                f"{idx:<5} {match.runbook_id:<15} {match.similarity_score:<22.4f} "
                f"{match.provenance_confidence:<24.2f} {match.prior_success_count:<18} {match.historical_fix}"
            )

    except Exception as err:
        print(f"Local PostgreSQL Database Status: Offline / Not Connected ({err})")
        print("Note: Unit tests verified with mocks; real pgvector verification not available.")
        print("Retrieval requires a running PostgreSQL instance with pgvector extension.")

    print("\nProvenance Confidence & Feedback Mechanics (Demo Simulation)")
    print("------------------------------------------------------------")
    print("Demonstrating self-correcting feedback updates (Simulated Execution Outcome):\n")

    target_rb = runbooks[0]
    print(f"Target Runbook: {target_rb.runbook_id} ({target_rb.title})")

    # Simulation 1: SUCCESS
    conf_succ, count_succ = update_provenance_confidence(
        current_confidence=target_rb.provenance_confidence,
        prior_success_count=target_rb.prior_success_count,
        outcome="SUCCESS",
    )
    print("\nScenario 1: Resolution Execution Succeeded")
    print(f"  BEFORE  : Confidence = {target_rb.provenance_confidence:.2f}, Success Count = {target_rb.prior_success_count}")
    print("  OUTCOME : SUCCESS (+0.05 confidence reward, +1 success count)")
    print(f"  AFTER   : Confidence = {conf_succ:.2f}, Success Count = {count_succ}")

    # Simulation 2: FAILURE
    conf_fail, count_fail = update_provenance_confidence(
        current_confidence=target_rb.provenance_confidence,
        prior_success_count=target_rb.prior_success_count,
        outcome="FAILURE",
    )
    print("\nScenario 2: Resolution Execution Failed")
    print(f"  BEFORE  : Confidence = {target_rb.provenance_confidence:.2f}, Success Count = {target_rb.prior_success_count}")
    print("  OUTCOME : FAILURE (-0.10 confidence penalty, success count preserved)")
    print(f"  AFTER   : Confidence = {conf_fail:.2f}, Success Count = {count_fail}")


if __name__ == "__main__":
    run_demo()
