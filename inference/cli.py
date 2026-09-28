"""Interactive CLI Dashboard for SovereignOps Air-Gapped Triage.

Provides an operational command-line interface for SREs to trigger the
autonomous multi-tier diagnostic and remediation reasoning loop.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure project root and current directory are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_DIR))

from orchestrator import run_triage_loop

ASCII_HEADER = r"""
================================================================================
  ____                             _             ___             
 / ___|  _____   _____ _ __ ___   (_) __ _ _ __ / _ \ _ __  ___ 
 \___ \ / _ \ \ / / _ \ '__/ _ \  | |/ _` | '_ \ | | | '_ \/ __|
  ___) | (_) \ V /  __/ | |  __/  | | (_| | | | || |_| | |_) \__ \
 |____/ \___/ \_/ \___|_|  \___|  |_|\__, |_| |_| \___/| .__/|___/
                                     |___/             |_|        
             SOVEREIGNOPS AIR-GAPPED INCIDENT TRIAGE CLI
================================================================================
"""


def render_triage_dashboard(alert_id: str) -> None:
    """Run interactive triage session and render human-readable dashboard.

    Args:
        alert_id: Identifier of the alert to triage.
    """
    # Mute background warning logs from LLM client for clean UI rendering
    logging.getLogger("llm_client").setLevel(logging.ERROR)
    logging.getLogger("orchestrator").setLevel(logging.ERROR)

    print(ASCII_HEADER)
    print(f"  [SESSION] Active Alert ID : {alert_id}")
    print("  [MODE]    Air-Gapped Local Inference (Zero Network Egress)")
    print("=" * 80)
    sys.stdout.flush()

    # Step 1: Ingestion status
    print("\n[*] Ingesting local telemetry (alerts, syslogs, and runbooks)...")
    time.sleep(0.5)
    print("[*] Ingestion complete. Telemetry indexed in air-gapped memory.")
    sys.stdout.flush()

    # Step 2: Diagnostic status
    print("\n[*] Evaluating Tier-1 Diagnostics via local LLM reasoning...")
    time.sleep(0.5)

    # Execute orchestrator loop
    results = run_triage_loop(alert_id, verbose=False)

    diagnostic = results.get("diagnostic", {})
    diag_payload = diagnostic.get("payload", {})
    diag_cmd = diag_payload.get("command", "N/A")
    diag_target = diag_payload.get("target_node", "N/A")
    diag_action = diagnostic.get("action_type", "tier_1_diagnostic")

    # Display Phase 1 Diagnostics
    print("\n" + "-" * 80)
    print("  [PHASE 1: TIER-1 DIAGNOSTIC DISCOVERY]")
    print("-" * 80)
    print(f"  Action Type    : {diag_action}")
    print(f"  Target Node    : {diag_target}")
    print(f"  Diagnostic Cmd : {diag_cmd}")
    print("  Execution Tier : Tier-1 (Read-Only / Non-Destructive)")
    print("  Policy Status  : AUTO-APPROVED (Simulated Execution)")
    print("-" * 80)
    sys.stdout.flush()

    # Step 3: Sovereign Graph & Provenance Reasoning
    print("\n[*] Querying Sovereign Graph & Provenance Memory...")
    time.sleep(0.5)

    graph_context = results.get("graph_context", {})
    traced = graph_context.get("traced_root_cause", {})
    root_node = traced.get("node_id", "Unknown")
    pagerank = traced.get("criticality_pagerank_score", "N/A")
    path_nodes = traced.get("path_from_trigger", [])
    path_str = " -> ".join(path_nodes) if path_nodes else "N/A"

    matches = graph_context.get("provenance_memory_matches", [])
    if matches:
        rb_match = matches[0]
        rb_id = rb_match.get("runbook_id", "N/A")
        confidence = rb_match.get("provenance_confidence", 0.0)
        conf_str = f"{confidence * 100:.1f}%"
        success_count = rb_match.get("prior_success_count", 0)
    else:
        rb_id = "N/A"
        conf_str = "N/A"
        success_count = 0

    print(f"  + Traced Root Cause Node : {root_node} (PageRank Score: {pagerank})")
    print(f"  + Trigger Dependency Path : {path_str}")
    print(f"  + Matched Runbook        : {rb_id} (Confidence: {conf_str}, Prior Successes: {success_count})")
    sys.stdout.flush()

    # Step 4: Remediation Plan formulation
    print("\n[*] Synthesizing Tier-2 Remediation plan with Local LLM reasoning...")
    time.sleep(0.5)

    remediation = results.get("remediation", {})
    rem_payload = remediation.get("payload", {})
    rem_cmd = rem_payload.get("command", "N/A")
    rem_target = rem_payload.get("target_node", "N/A")
    rem_justification = rem_payload.get("justification", "N/A")
    rem_action = remediation.get("action_type", "tier_2_remediation")

    # Display Phase 2 Remediation
    print("\n" + "=" * 80)
    print("  [PHASE 2: TIER-2 REMEDIATION PROPOSAL]")
    print("=" * 80)
    print(f"  Target Node       : {rem_target}")
    print(f"  Action Type       : {rem_action}")
    print(f"  Proposed Command  : {rem_cmd}")
    print("\n  Justification:")
    print(f"    {rem_justification}")
    print("\n" + "-" * 80)
    print("  >>> REQUIRED HUMAN OPERATOR SIGN-OFF (TIER-2 GATEWAY) <<<")
    print("-" * 80)
    print("  [!] WARNING: Tier-2 actions alter live cluster state and require human sign-off.")
    print("  Autonomous execution is halted per sovereign safety policies.")
    print(f"\n  Action Pending Approval : {rem_cmd}")
    print(f"  Target Node             : {rem_target}")
    print("  Required Role           : SRE On-Call Lead")
    print("  Approval Status         : [!] AWAITING OPERATOR CONFIRMATION [!]")
    print("=" * 80 + "\n")
    sys.stdout.flush()


def main() -> None:
    """Parse CLI arguments and launch triage dashboard."""
    parser = argparse.ArgumentParser(
        description="SovereignOps Air-Gapped Triage Dashboard CLI",
    )
    parser.add_argument(
        "--alert-id",
        type=str,
        default="INC-8891",
        help="Alert identifier to triage (default: INC-8891)",
    )
    args = parser.parse_args()
    render_triage_dashboard(args.alert_id)


if __name__ == "__main__":
    main()
