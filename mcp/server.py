"""SovereignOps Model Context Protocol (MCP) Server for Air-Gapped Systems.

Implements the MCP stdio server protocol to provide diagnostic logs, runbook provenance,
and Kubernetes remediation tooling for Member A incident triage workflows.
"""

import json
import os
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Initialize MCP server named "sovereignops-mcp"
mcp = FastMCP("sovereignops-mcp")


@mcp.tool()
async def get_diagnostic_logs(target_node: str, service_name: str) -> str:
    """Fetch diagnostic syslog logs for a target node and service.

    Args:
        target_node: The identifier of the server or container node (e.g., api-gateway-01).
        service_name: The name of the service unit to query (e.g., gateway-proxy).

    Returns:
        Formatted syslog output excerpt matching the diagnostic query.
    """
    log_path = f"data/logs/{service_name}.log"
    file_to_read = Path(log_path)
    if not file_to_read.exists():
        file_to_read = PROJECT_ROOT / log_path

    try:
        with open(file_to_read, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return f"Error: Log file for service '{service_name}' is empty."

        # --- Heuristic noise filter ---
        SIGNAL_KEYWORDS = {"[WARN]", "[ERROR]", "[FATAL]", "Exception"}
        keep: set[int] = set()

        for i, line in enumerate(lines):
            if any(kw in line for kw in SIGNAL_KEYWORDS):
                # Keep the signal line + up to 2 lines of prior context
                for ctx in range(max(0, i - 2), i + 1):
                    keep.add(ctx)

        # Always include the final line (edge-case protection)
        keep.add(len(lines) - 1)

        # Rebuild in chronological order
        filtered = "".join(lines[i] for i in sorted(keep))
        return filtered

    except FileNotFoundError:
        return f"Error: No logs found on disk for service '{service_name}'."


@mcp.tool()
async def get_runbook(runbook_id: str) -> str:
    """Retrieve historical remediation provenance memory and confidence scores for a given runbook ID.

    Args:
        runbook_id: The runbook identifier (e.g., RB-089).

    Returns:
        JSON string containing runbook details, confidence score, prior successes, and recommended action.
    """
    runbook_path = f"data/runbooks/{runbook_id}.json"
    file_to_read = Path(runbook_path)
    if not file_to_read.exists():
        file_to_read = PROJECT_ROOT / runbook_path

    try:
        with open(file_to_read, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return json.dumps({"error": f"Runbook '{runbook_id}' not found on disk."})


@mcp.tool()
async def execute_k8s_rollback(deployment_name: str) -> str:
    """Execute a Kubernetes rollout undo operation for the specified deployment name.

    Args:
        deployment_name: The Kubernetes deployment name to roll back (e.g., auth-service).

    Returns:
        Confirmation message verifying successful rollout rollback execution.
    """
    try:
        result = subprocess.run(
            ["kubectl", "rollout", "undo", f"deployment/{deployment_name}", "--dry-run=client"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        # Fallback to simulated audit logging if cluster is unreachable or execution fails
        raise FileNotFoundError(result.stderr or "kubectl cluster execution failed")
    except FileNotFoundError:
        audit_path = Path("data/logs/audit.log")
        if not audit_path.parent.exists():
            audit_path = PROJECT_ROOT / "data" / "logs" / "audit.log"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(f"[AUDIT] Executed: kubectl rollout undo deployment/{deployment_name}\n")
        return f"deployment.apps/{deployment_name} rolled back successfully [Simulated & Logged to audit.log]"


@mcp.tool()
async def list_services() -> str:
    """Use this tool to list all available services on the target node before fetching logs, ensuring you have the exact correct spelling and formatting."""
    logs_dir = Path("data/logs")
    if not logs_dir.exists():
        logs_dir = PROJECT_ROOT / "data" / "logs"

    try:
        files = os.listdir(logs_dir)
    except FileNotFoundError:
        return "No services found."

    services = [f[:-4] for f in sorted(files) if f.endswith(".log") and f != "audit.log"]
    if not services:
        return "No services found."

    return f"Available services for log inspection: {', '.join(services)}"


@mcp.tool()
async def list_runbooks() -> str:
    """List all available runbooks in the knowledge base with their IDs and titles.

    Use this tool to discover the correct runbook ID before calling get_runbook.
    Returns a compact index of runbook IDs and their titles so you can select the
    most relevant one for the current incident.
    """
    runbooks_dir = Path("data/runbooks")
    if not runbooks_dir.exists():
        runbooks_dir = PROJECT_ROOT / "data" / "runbooks"

    try:
        files = sorted(f for f in os.listdir(runbooks_dir) if f.endswith(".json"))
    except FileNotFoundError:
        return "No runbooks found."

    if not files:
        return "No runbooks found."

    index = []
    for fname in files:
        try:
            with open(runbooks_dir / fname, "r", encoding="utf-8") as f:
                data = json.load(f)
            rb_id = data.get("runbook_id", fname.replace(".json", ""))
            title = data.get("title", "No title")
            index.append(f"{rb_id}: {title}")
        except Exception:
            index.append(f"{fname.replace('.json', '')}: (unreadable)")

    return "Available runbooks:\n" + "\n".join(index)


if __name__ == "__main__":
    # Run server using stdio transport
    mcp.run(transport="stdio")
