"""Local Inference module for SovereignOps.

Combines ingested telemetry data with graph context (Contract B) to produce
remediation decisions (Contract D) via local LLM or graceful fallback.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sub_team_1.data_ingestion.ingest import ingest_incident_data
from sub_team_1.local_inference.llm_client import query_local_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
MOCK_CONTRACT_B_PATH = CURRENT_DIR / "mock_contract_b.json"


def load_context(alert_id: str = "INC-8891") -> Dict[str, Any]:
    """Load ingested incident data and graph context (Contract B).

    Args:
        alert_id: Identifier of the alert to ingest. Defaults to "INC-8891".

    Returns:
        Dict containing telemetry data and graph context.
    """
    incident_telemetry = ingest_incident_data(alert_id)

    if not MOCK_CONTRACT_B_PATH.exists():
        raise FileNotFoundError(f"Mock Contract B file not found: {MOCK_CONTRACT_B_PATH}")

    with open(MOCK_CONTRACT_B_PATH, "r", encoding="utf-8") as f:
        graph_context = json.load(f)

    return {
        "telemetry": incident_telemetry,
        "graph_context": graph_context,
    }


if __name__ == "__main__":
    context = load_context("INC-8891")
    decision = query_local_llm(context)
    print(json.dumps(decision, indent=2))
