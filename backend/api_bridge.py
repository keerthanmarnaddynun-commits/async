"""FastAPI bridge connecting the Linear-inspired React dashboard to SovereignOps orchestrator."""

import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root and inference paths are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INFERENCE_DIR = PROJECT_ROOT / "inference"

for path in [str(PROJECT_ROOT), str(INFERENCE_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from inference.orchestrator import run_triage_loop

app = FastAPI(
    title="SovereignOps Triage API Bridge",
    description="Air-gapped triage and remediation inference bridge for Member A dashboard",
    version="1.0.0",
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/triage/{alert_id}")
async def get_triage(alert_id: str) -> Dict[str, Any]:
    """Execute triage loop for the specified incident alert."""
    try:
        result = run_triage_loop(alert_id, verbose=True)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_bridge:app", host="0.0.0.0", port=8000, reload=True)
