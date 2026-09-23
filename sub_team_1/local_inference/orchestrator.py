"""Multi-step reasoning orchestrator for SovereignOps Local Inference.

Executes a two-step reasoning loop:
1. Tier-1 diagnostic pass based on alert telemetry and syslog.
2. Tier-2 remediation pass based on graph mapping (Contract B) and retrieved runbook.
Prompts the local LLM using schemas defined in Contract C.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root and current directory are on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_DIR))

from sub_team_1.data_ingestion.ingest import (
    ingest_all_runbooks,
    ingest_incident_data,
)
from llm_client import query_local_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

MOCK_CONTRACT_B_PATH = LOCAL_DIR / "mock_contract_b.json"

# Tool Schemas (Contract C)
TIER_1_SCHEMA: Dict[str, Any] = {
    "action_type": "tier_1_diagnostic",
    "payload": {
        "command": "<str>",
        "target_node": "<str>",
    },
}

TIER_2_SCHEMA: Dict[str, Any] = {
    "action_type": "tier_2_remediation",
    "payload": {
        "command": "<str>",
        "justification": "<str>",
        "target_node": "<str>",
    },
}


def run_triage_loop(alert_id: str, verbose: bool = True) -> Dict[str, Any]:
    """Execute two-step triage reasoning loop (Tier-1 diagnostic then Tier-2 remediation).

    Args:
        alert_id: Identifier of the alert to ingest and triage.
        verbose: Whether to log and print raw JSON payloads. Defaults to True.

    Returns:
        Dict containing diagnostic and remediation decisions, plus context.
    """
    # Step 1: Ingest alert, syslog, runbooks, and graph context (Contract B)
    incident_data = ingest_incident_data(alert_id)
    alert = incident_data["alert"]
    syslog = incident_data["syslog"]

    runbooks = ingest_all_runbooks()

    if not MOCK_CONTRACT_B_PATH.exists():
        raise FileNotFoundError(f"Mock Contract B file not found: {MOCK_CONTRACT_B_PATH}")

    with open(MOCK_CONTRACT_B_PATH, "r", encoding="utf-8") as f:
        graph_context = json.load(f)

    # Step 2: Diagnostic Pass (Tier-1)
    if verbose:
        logger.info("[Phase 1: Diagnostics]")
    diagnostic_prompt = (
        "You are an autonomous air-gapped site reliability engineering agent.\n"
        "Investigate the service crash based ONLY on the alert and syslog telemetry.\n\n"
        f"Alert Telemetry:\n{json.dumps(alert, indent=2)}\n\n"
        f"Syslog:\n{syslog}\n\n"
        "Output ONLY a valid JSON object matching the following schema (Contract C - Tier 1 Diagnostic):\n"
        f"{json.dumps(TIER_1_SCHEMA, indent=2)}\n"
    )
    diagnostic_decision = query_local_llm(diagnostic_prompt)
    payload_diag = diagnostic_decision.get("payload", {})
    command_diag = payload_diag.get("command", "")
    target_diag = payload_diag.get("target_node", "")
    if verbose:
        logger.info(f"Simulated tool call: command='{command_diag}' on target_node='{target_diag}'")
        print(json.dumps(diagnostic_decision, indent=2), flush=True)

    # Match relevant runbook from provenance matches if available
    matched_runbook = None
    matches = graph_context.get("provenance_memory_matches", [])
    if matches:
        target_rb_id = matches[0].get("runbook_id")
        for rb in runbooks:
            if rb.get("runbook_id") == target_rb_id:
                matched_runbook = rb.get("content")
                break
    if not matched_runbook and runbooks:
        matched_runbook = runbooks[0].get("content")

    # Step 3: Remediation Pass (Tier-2)
    if verbose:
        logger.info("[Phase 2: Remediation]")
    remediation_prompt = (
        "You are an autonomous air-gapped site reliability engineering agent.\n"
        "Determine the remediation action based on the infrastructure graph mapping (Contract B) and retrieved runbook.\n\n"
        f"Graph Mapping (Contract B):\n{json.dumps(graph_context, indent=2)}\n\n"
        f"Retrieved Runbook:\n{matched_runbook or 'No runbook found'}\n\n"
        "Output ONLY a valid JSON object matching the following schema (Contract C - Tier 2 Remediation):\n"
        f"{json.dumps(TIER_2_SCHEMA, indent=2)}\n"
    )
    remediation_decision = query_local_llm(remediation_prompt)
    payload_rem = remediation_decision.get("payload", {})
    command_rem = payload_rem.get("command", "")
    target_rem = payload_rem.get("target_node", "")
    justification_rem = payload_rem.get("justification", "")
    if verbose:
        logger.info(
            f"Proposed remediation: command='{command_rem}' on target_node='{target_rem}' "
            f"(justification: {justification_rem})"
        )
        print(json.dumps(remediation_decision, indent=2), flush=True)

    return {
        "alert_id": alert_id,
        "telemetry": incident_data,
        "graph_context": graph_context,
        "matched_runbook": matched_runbook,
        "diagnostic": diagnostic_decision,
        "remediation": remediation_decision,
    }


if __name__ == "__main__":
    run_triage_loop("INC-8891")
