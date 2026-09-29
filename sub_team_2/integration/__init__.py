"""
Team 2 Integration Package

Provides the thin orchestration layer joining Infrastructure Graph structural fault localization
with Provenance Memory Store historical runbook retrieval.
"""

import sys
import importlib.util
from pathlib import Path

_base_dir = Path(__file__).resolve().parent.parent
_infra_path = str(_base_dir / "infrastructure_graph")
_memory_path = str(_base_dir / "provenance_memory")

# 1. Setup sys.path with infrastructure_graph and provenance_memory
if _infra_path not in sys.path:
    sys.path.insert(0, _infra_path)
if _memory_path not in sys.path:
    sys.path.insert(1, _memory_path)

# 2. Merge contracts.schemas modules to prevent namespace collision
try:
    import contracts.schemas as cs_infra
    mem_schema_path = Path(_memory_path) / "contracts" / "schemas.py"
    if mem_schema_path.exists():
        spec = importlib.util.spec_from_file_location("contracts.schemas_memory", mem_schema_path)
        mem_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mem_mod)
        for attr in dir(mem_mod):
            if not hasattr(cs_infra, attr):
                setattr(cs_infra, attr, getattr(mem_mod, attr))
except Exception:
    pass

from .schemas import Team2IncidentAnalysisSchema
from .orchestrator import Team2Orchestrator

__all__ = [
    "Team2IncidentAnalysisSchema",
    "Team2Orchestrator",
]
