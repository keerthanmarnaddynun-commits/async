"""
Provenance Memory Store Package

Provides internal representations, storage abstractions, embedding vector interfaces,
similarity retrieval, and provenance confidence scoring for historical incident runbooks.
"""

from .models import HistoricalRunbook, RunbookMatch, RetrievedRunbookMatch, load_mock_runbooks
from .storage import PostgresMemoryStore
from .embeddings import LocalEmbeddingModel
from .retrieval import ProvenanceMemoryRetriever, build_memory_output
from .confidence import (
    ConfidenceUpdateResult,
    update_provenance_confidence,
    ProvenanceConfidenceManager,
)

__all__ = [
    "HistoricalRunbook",
    "RunbookMatch",
    "RetrievedRunbookMatch",
    "load_mock_runbooks",
    "PostgresMemoryStore",
    "LocalEmbeddingModel",
    "ProvenanceMemoryRetriever",
    "build_memory_output",
    "ConfidenceUpdateResult",
    "update_provenance_confidence",
    "ProvenanceConfidenceManager",
]
