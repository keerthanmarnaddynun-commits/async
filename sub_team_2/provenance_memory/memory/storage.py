"""
Storage Module

Provides PostgreSQL database connectivity and pgvector schema operations for historical incident runbooks.
"""

import os
from typing import List, Optional, Sequence
import psycopg
from .models import HistoricalRunbook, RetrievedRunbookMatch

DEFAULT_POSTGRES_URI = os.getenv(
    "POSTGRES_URI", "postgresql://sovereign_user:sovereign_pass@localhost:5432/sovereign_ops"
)


class PostgresMemoryStore:
    """Manages PostgreSQL connection lifecycle and CRUD operations for HistoricalRunbook vectors."""

    def __init__(self, connection_string: str = DEFAULT_POSTGRES_URI):
        if not connection_string or not isinstance(connection_string, str):
            raise ValueError("Connection string must be a non-empty string.")
        self.connection_string: str = connection_string
        self.connection: Optional[psycopg.Connection] = None

    def connect(self) -> psycopg.Connection:
        """Establishes a connection to the PostgreSQL database."""
        if self.connection is None or self.connection.closed:
            try:
                self.connection = psycopg.connect(self.connection_string, connect_timeout=2)
            except Exception as err:
                raise RuntimeError(f"Failed to connect to PostgreSQL database: {err}") from err
        return self.connection

    def close(self) -> None:
        """Closes the PostgreSQL database connection if open."""
        if self.connection is not None and not self.connection.closed:
            try:
                self.connection.close()
            finally:
                self.connection = None

    def initialize_schema(self) -> None:
        """Enables the pgvector extension and creates the historical_runbooks table schema."""
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS historical_runbooks (
                        id SERIAL PRIMARY KEY,
                        runbook_id TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        error_signature TEXT NOT NULL,
                        historical_fix TEXT NOT NULL,
                        provenance_confidence DOUBLE PRECISION NOT NULL,
                        prior_success_count INTEGER NOT NULL,
                        embedding VECTOR
                    );
                    """
                )
            conn.commit()
        except Exception as err:
            conn.rollback()
            raise RuntimeError(
                f"Failed to initialize PostgreSQL schema / pgvector extension: {err}"
            ) from err

    def insert_runbook(self, runbook: HistoricalRunbook) -> None:
        """Inserts or updates a historical runbook record in the database using parameterized SQL."""
        if not isinstance(runbook, HistoricalRunbook):
            raise ValueError("Input must be a valid HistoricalRunbook model instance.")

        conn = self.connect()
        query = """
            INSERT INTO historical_runbooks (
                runbook_id, title, error_signature, historical_fix,
                provenance_confidence, prior_success_count, embedding
            ) VALUES (%s, %s, %s, %s, %s, %s, NULL)
            ON CONFLICT (runbook_id) DO UPDATE SET
                title = EXCLUDED.title,
                error_signature = EXCLUDED.error_signature,
                historical_fix = EXCLUDED.historical_fix,
                provenance_confidence = EXCLUDED.provenance_confidence,
                prior_success_count = EXCLUDED.prior_success_count;
        """
        params = (
            runbook.runbook_id,
            runbook.title,
            runbook.error_signature,
            runbook.historical_fix,
            runbook.provenance_confidence,
            runbook.prior_success_count,
        )

        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()
        except Exception as err:
            conn.rollback()
            raise RuntimeError(f"Database insert failed for runbook '{runbook.runbook_id}': {err}") from err

    def update_embedding(self, runbook_id: str, embedding: Sequence[float]) -> bool:
        """Updates the vector embedding column for a specific runbook_id using parameterized SQL."""
        if not runbook_id or not isinstance(runbook_id, str):
            raise ValueError("runbook_id must be a non-empty string.")

        if not isinstance(embedding, (list, tuple)) or len(embedding) == 0:
            raise ValueError("Embedding must be a non-empty list or tuple of numeric values.")

        try:
            float_vector = [float(x) for x in embedding]
        except (ValueError, TypeError) as err:
            raise ValueError(f"All elements in embedding must be convertible to float: {err}") from err

        conn = self.connect()
        vector_str = f"[{','.join(str(x) for x in float_vector)}]"
        query = "UPDATE historical_runbooks SET embedding = %s::vector WHERE runbook_id = %s;"

        try:
            with conn.cursor() as cur:
                cur.execute(query, (vector_str, runbook_id))
                updated = cur.rowcount > 0
            conn.commit()
            return updated
        except Exception as err:
            conn.rollback()
            raise RuntimeError(f"Database update_embedding failed for runbook '{runbook_id}': {err}") from err

    def update_provenance(
        self, runbook_id: str, provenance_confidence: float, prior_success_count: int
    ) -> bool:
        """
        Updates provenance_confidence and prior_success_count for a specific runbook_id.
        Does NOT modify embedding, title, error_signature, or historical_fix.

        Args:
            runbook_id: Non-empty string runbook identifier.
            provenance_confidence: Float between 0.0 and 1.0.
            prior_success_count: Integer >= 0.

        Returns:
            bool: True if record was updated, False otherwise.
        """
        if not runbook_id or not isinstance(runbook_id, str):
            raise ValueError("runbook_id must be a non-empty string.")

        if isinstance(provenance_confidence, bool) or not isinstance(provenance_confidence, (int, float)):
            raise TypeError("provenance_confidence must be a float or int.")
        provenance_confidence = float(provenance_confidence)
        if provenance_confidence < 0.0 or provenance_confidence > 1.0:
            raise ValueError("provenance_confidence must be between 0.0 and 1.0.")

        if isinstance(prior_success_count, bool) or not isinstance(prior_success_count, int):
            raise TypeError("prior_success_count must be an integer.")
        if prior_success_count < 0:
            raise ValueError("prior_success_count must be >= 0.")

        conn = self.connect()
        query = """
            UPDATE historical_runbooks
            SET provenance_confidence = %s,
                prior_success_count = %s
            WHERE runbook_id = %s;
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, (provenance_confidence, prior_success_count, runbook_id))
                updated = cur.rowcount > 0
            conn.commit()
            return updated
        except Exception as err:
            conn.rollback()
            raise RuntimeError(f"Database update_provenance failed for runbook '{runbook_id}': {err}") from err

    def get_runbook(self, runbook_id: str) -> Optional[HistoricalRunbook]:
        """Retrieves a historical runbook by its runbook_id using parameterized SQL."""
        if not runbook_id or not isinstance(runbook_id, str):
            raise ValueError("runbook_id must be a non-empty string.")

        conn = self.connect()
        query = """
            SELECT runbook_id, title, error_signature, historical_fix,
                   provenance_confidence, prior_success_count
            FROM historical_runbooks
            WHERE runbook_id = %s;
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, (runbook_id,))
                row = cur.fetchone()
                if row is None:
                    return None

                return HistoricalRunbook(
                    runbook_id=row[0],
                    title=row[1],
                    error_signature=row[2],
                    historical_fix=row[3],
                    provenance_confidence=float(row[4]),
                    prior_success_count=int(row[5]),
                )
        except Exception as err:
            raise RuntimeError(f"Database query failed for runbook '{runbook_id}': {err}") from err

    def list_runbooks(self) -> List[HistoricalRunbook]:
        """Retrieves all historical runbooks sorted deterministically by runbook_id."""
        conn = self.connect()
        query = """
            SELECT runbook_id, title, error_signature, historical_fix,
                   provenance_confidence, prior_success_count
            FROM historical_runbooks
            ORDER BY runbook_id ASC;
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                results = []
                for row in rows:
                    results.append(
                        HistoricalRunbook(
                            runbook_id=row[0],
                            title=row[1],
                            error_signature=row[2],
                            historical_fix=row[3],
                            provenance_confidence=float(row[4]),
                            prior_success_count=int(row[5]),
                        )
                    )
                return results
        except Exception as err:
            raise RuntimeError(f"Database list query failed: {err}") from err

    def delete_runbook(self, runbook_id: str) -> bool:
        """Deletes a historical runbook record by runbook_id using parameterized SQL."""
        if not runbook_id or not isinstance(runbook_id, str):
            raise ValueError("runbook_id must be a non-empty string.")

        conn = self.connect()
        query = "DELETE FROM historical_runbooks WHERE runbook_id = %s;"
        try:
            with conn.cursor() as cur:
                cur.execute(query, (runbook_id,))
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        except Exception as err:
            conn.rollback()
            raise RuntimeError(f"Database delete failed for runbook '{runbook_id}': {err}") from err

    def search_similar(
        self, query_embedding: Sequence[float], top_k: int = 5
    ) -> List[RetrievedRunbookMatch]:
        """
        Executes vector similarity search using pgvector cosine distance.
        Ignores runbooks with NULL embeddings. Orders by similarity (cosine distance)
        and breaks ties alphabetically by runbook_id.

        Args:
            query_embedding: Sequence of numeric vector values.
            top_k: Positive integer representing maximum matches to return. Defaults to 5.

        Returns:
            List[RetrievedRunbookMatch]: Matched runbooks ordered by cosine similarity score.
        """
        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise TypeError("top_k must be an integer.")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if not isinstance(query_embedding, (list, tuple)) or len(query_embedding) == 0:
            raise ValueError("query_embedding must be a non-empty list or tuple of numeric values.")

        try:
            float_vector = [float(x) for x in query_embedding]
        except (ValueError, TypeError) as err:
            raise ValueError(f"All elements in query_embedding must be convertible to float: {err}") from err

        vector_str = f"[{','.join(str(x) for x in float_vector)}]"
        conn = self.connect()
        query = """
            SELECT
                runbook_id,
                historical_fix,
                provenance_confidence,
                prior_success_count,
                1 - (embedding <=> %s::vector) AS similarity_score
            FROM historical_runbooks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector ASC, runbook_id ASC
            LIMIT %s;
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, (vector_str, vector_str, top_k))
                rows = cur.fetchall()
                results = []
                for row in rows:
                    raw_score = float(row[4])
                    clamped_score = max(-1.0, min(1.0, raw_score))
                    results.append(
                        RetrievedRunbookMatch(
                            runbook_id=row[0],
                            historical_fix=row[1],
                            provenance_confidence=float(row[2]),
                            prior_success_count=int(row[3]),
                            similarity_score=clamped_score,
                        )
                    )
                return results
        except Exception as err:
            conn.rollback()
            raise RuntimeError(f"Database search_similar failed: {err}") from err
