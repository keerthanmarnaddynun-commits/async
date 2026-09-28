"""Data ingestion package."""
from .ingest import ingest_all_runbooks, ingest_incident_data, setup_mock_data

__all__ = ["ingest_incident_data", "setup_mock_data", "ingest_all_runbooks"]
