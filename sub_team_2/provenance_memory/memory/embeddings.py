"""
Embeddings Module

Provides local vector embedding generation for historical runbooks and incident context using
sentence-transformers (default: sentence-transformers/all-MiniLM-L6-v2).
Executes 100% locally without external APIs.
"""

from typing import Any, List, Union
from sentence_transformers import SentenceTransformer

from memory.models import HistoricalRunbook

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class LocalEmbeddingModel:
    """
    Local embedding generator wrapping sentence-transformers for offline semantic encoding.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        if not model_name or not isinstance(model_name, str):
            raise ValueError("model_name must be a non-empty string.")
        self.model_name: str = model_name
        self._model: Any = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-loads the SentenceTransformer model instance."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def embedding_dimension(self) -> int:
        """Returns the output vector dimension of the loaded embedding model."""
        dim = self.model.get_sentence_embedding_dimension()
        return int(dim) if dim is not None else 384

    def construct_runbook_text(self, runbook: HistoricalRunbook) -> str:
        """
        Formats semantic text for a runbook by concatenating title, error signature, and fix.
        Excludes metadata signals (provenance_confidence and prior_success_count).
        """
        if not isinstance(runbook, HistoricalRunbook):
            raise TypeError("Input must be a valid HistoricalRunbook model instance.")

        return f"Title:\n{runbook.title}\n\nError Signature:\n{runbook.error_signature}\n\nHistorical Fix:\n{runbook.historical_fix}"

    def embed_text(self, text: str) -> List[float]:
        """
        Encodes a single text string into a float vector embedding.
        """
        if not isinstance(text, str):
            raise TypeError("Input text must be a string.")
        if not text.strip():
            raise ValueError("Input text cannot be empty or whitespace.")

        vector = self.model.encode(text, convert_to_numpy=True)
        return [float(x) for x in vector]

    def embed_runbook(self, runbook: HistoricalRunbook) -> List[float]:
        """
        Generates a vector embedding for a HistoricalRunbook instance.
        """
        text = self.construct_runbook_text(runbook)
        return self.embed_text(text)

    def embed_many(self, runbooks: List[HistoricalRunbook]) -> List[List[float]]:
        """
        Generates vector embeddings for a list of HistoricalRunbook instances.
        """
        if not isinstance(runbooks, list):
            raise TypeError("Input runbooks must be a list of HistoricalRunbook instances.")

        texts = []
        for idx, rb in enumerate(runbooks):
            if not isinstance(rb, HistoricalRunbook):
                raise TypeError(f"Item at index {idx} must be a valid HistoricalRunbook model instance.")
            texts.append(self.construct_runbook_text(rb))

        if not texts:
            return []

        vectors = self.model.encode(texts, convert_to_numpy=True)
        return [[float(x) for x in vec] for vec in vectors]
