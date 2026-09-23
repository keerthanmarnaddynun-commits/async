"""Local air-gapped data ingestion layer for SovereignOps.

Provides local mock telemetry ingestion without any network egress.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

# Configure structured local logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "raw_data"
ALERTS_DIR = RAW_DATA_DIR / "alerts"
SYSLOGS_DIR = RAW_DATA_DIR / "syslogs"

MOCK_ALERT_ID = "INC-8891"
MOCK_SERVICE = "api-gateway-01"

MOCK_ALERT_DATA = {
    "alert_id": MOCK_ALERT_ID,
    "timestamp": "2026-09-23T19:30:00Z",
    "triggering_service": MOCK_SERVICE,
    "error_signature": "HTTP 503 Service Unavailable",
    "severity": "CRITICAL",
}

MOCK_SYSLOG_DATA = (
    "Sep 23 19:29:45 api-gateway-01 systemd[1]: Starting API Gateway...\n"
    "Sep 23 19:29:50 api-gateway-01 gateway-proxy[4432]: [WARN] Connection pool reaching capacity\n"
    "Sep 23 19:30:00 api-gateway-01 gateway-proxy[4432]: [ERROR] HTTP 503 Service Unavailable - upstream auth-service timeout\n"
    "Sep 23 19:30:01 api-gateway-01 systemd[1]: gateway-proxy.service: Main process exited, code=exited, status=1/FAILURE\n"
)


def setup_mock_data() -> None:
    """Ensure raw_data directories and sample telemetry files exist."""
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    SYSLOGS_DIR.mkdir(parents=True, exist_ok=True)

    alert_file = ALERTS_DIR / f"{MOCK_ALERT_ID}.json"
    if not alert_file.exists():
        logger.info(f"Creating mock alert file at {alert_file}")
        with open(alert_file, "w", encoding="utf-8") as f:
            json.dump(MOCK_ALERT_DATA, f, indent=2)

    syslog_file = SYSLOGS_DIR / f"{MOCK_SERVICE}.log"
    if not syslog_file.exists():
        logger.info(f"Creating mock syslog file at {syslog_file}")
        with open(syslog_file, "w", encoding="utf-8") as f:
            f.write(MOCK_SYSLOG_DATA)


def ingest_incident_data(alert_id: str) -> Dict[str, Any]:
    """Ingest incident telemetry and corresponding syslog into memory.

    Args:
        alert_id: Identifier of the incident alert to ingest.

    Returns:
        Dict containing parsed alert telemetry and raw syslog contents.

    Raises:
        FileNotFoundError: If the alert or associated syslog file does not exist.
    """
    alert_path = ALERTS_DIR / f"{alert_id}.json"
    if not alert_path.exists():
        raise FileNotFoundError(f"Alert file not found: {alert_path}")

    with open(alert_path, "r", encoding="utf-8") as f:
        alert_data = json.load(f)

    triggering_service = alert_data.get("triggering_service")
    if not triggering_service:
        raise ValueError(f"Missing 'triggering_service' in alert {alert_id}")

    syslog_path = SYSLOGS_DIR / f"{triggering_service}.log"
    if not syslog_path.exists():
        raise FileNotFoundError(f"Syslog file not found for service {triggering_service}: {syslog_path}")

    with open(syslog_path, "r", encoding="utf-8") as f:
        syslog_content = f.read()

    return {
        "alert": alert_data,
        "syslog": syslog_content,
    }


if __name__ == "__main__":
    setup_mock_data()
    payload = ingest_incident_data("INC-8891")
    print(json.dumps(payload, indent=2))
