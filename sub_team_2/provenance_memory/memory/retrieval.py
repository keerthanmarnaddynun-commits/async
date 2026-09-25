"""
Retrieval Module

Responsible for similarity-based vector search and ranking of historical runbooks given
an incident query or alert error signature context.
"""

from typing import List, Sequence
from .models import RetrievedRunbookMatch
from .storage import PostgresMemoryStore
from .embeddings import LocalEmbeddingModel
from contracts.schemas import (
    MemoryQuerySchema,
    ProvenanceMemoryMatchSchema,
    ProvenanceMemoryOutputSchema,
)


class ProvenanceMemoryRetriever:
    """Orchestrates embedding generation and PostgreSQL pgvector similarity queries."""

    def __init__(self, storage: PostgresMemoryStore, embedding_model: LocalEmbeddingModel):
        """
        Initializes the retriever with storage and local embedding components.

        Args:
            storage: PostgresMemoryStore instance.
            embedding_model: LocalEmbeddingModel instance.
        """
        if not isinstance(storage, PostgresMemoryStore):
            raise TypeError("storage must be an instance of PostgresMemoryStore.")
        if not isinstance(embedding_model, LocalEmbeddingModel):
            raise TypeError("embedding_model must be an instance of LocalEmbeddingModel.")

        self.storage: PostgresMemoryStore = storage
        self.embedding_model: LocalEmbeddingModel = embedding_model

    def search(self, query_text: str, top_k: int = 5) -> List[RetrievedRunbookMatch]:
        """
        Generates query embedding and searches for top-k semantically similar historical runbooks.

        Args:
            query_text: Non-empty semantic query string.
            top_k: Positive integer specifying max results to return. Defaults to 5.

        Returns:
            List[RetrievedRunbookMatch]: List of matching runbooks sorted by similarity.

        Raises:
            TypeError: If query_text is not a string or top_k is not an integer.
            ValueError: If query_text is empty or top_k <= 0.
        """
        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise TypeError("top_k must be an integer.")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if not isinstance(query_text, str) or not query_text.strip():
            raise ValueError("query_text must be a non-empty string.")

        query_embedding = self.embedding_model.embed_text(query_text)
        return self.storage.search_similar(query_embedding, top_k=top_k)

    def search_by_alert(self, alert: MemoryQuerySchema, top_k: int = 5) -> List[RetrievedRunbookMatch]:
        """
        Extracts error signature from an incident alert and searches for top-k similar runbooks.

        Args:
            alert: Validated MemoryQuerySchema object.
            top_k: Positive integer specifying max results to return. Defaults to 5.

        Returns:
            List[RetrievedRunbookMatch]: List of matching runbooks sorted by similarity.

        Raises:
            TypeError: If alert is not MemoryQuerySchema or top_k is not an integer.
            ValueError: If top_k <= 0.
        """
        if not isinstance(alert, MemoryQuerySchema):
            raise TypeError("alert must be an instance of MemoryQuerySchema.")

        semantic_query = f"Error Signature:\n{alert.error_signature}"
        return self.search(semantic_query, top_k=top_k)


def build_memory_output(
    alert_id: str, matches: Sequence[RetrievedRunbookMatch]
) -> ProvenanceMemoryOutputSchema:
    """
    Constructs an external ProvenanceMemoryOutputSchema contract object from internal retrieval matches.

    Args:
        alert_id: Unique alert identifier string.
        matches: Sequence of internal RetrievedRunbookMatch objects.

    Returns:
        ProvenanceMemoryOutputSchema: Validated output payload adhering to Team 2 contract.

    Raises:
        ValueError: If alert_id is empty or invalid.
        TypeError: If matches is not a sequence of RetrievedRunbookMatch objects.
    """
    if not isinstance(alert_id, str) or not alert_id.strip():
        raise ValueError("alert_id must be a non-empty string.")

    if not isinstance(matches, (list, tuple)):
        raise TypeError("matches must be a list or tuple of RetrievedRunbookMatch instances.")

    contract_matches = []
    for m in matches:
        if not isinstance(m, RetrievedRunbookMatch):
            raise TypeError("Each match must be an instance of RetrievedRunbookMatch.")
        contract_matches.append(
            ProvenanceMemoryMatchSchema(
                runbook_id=m.runbook_id,
                historical_fix=m.historical_fix,
                provenance_confidence=m.provenance_confidence,
                prior_success_count=m.prior_success_count,
            )
        )

    return ProvenanceMemoryOutputSchema(
        alert_id=alert_id.strip(),
        provenance_memory_matches=contract_matches,
    )
