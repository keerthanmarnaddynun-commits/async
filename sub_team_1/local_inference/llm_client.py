"""Local LLM client for SovereignOps.

Connects to a local Ollama instance (air-gapped) with graceful fallback
to mock Contract D payload when unreachable.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"

FALLBACK_TIER_1: Dict[str, Any] = {
    "action_type": "tier_1_diagnostic",
    "payload": {
        "command": "journalctl -u gateway-proxy -n 50",
        "target_node": "api-gateway-01",
    },
}

FALLBACK_CONTRACT_D: Dict[str, Any] = {
    "action_type": "tier_2_remediation",
    "payload": {
        "command": "kubectl rollout undo deployment/auth-service",
        "justification": (
            "Graph mapped fault to auth-service timeout. "
            "Historical provenance score 0.94 strongly supports rollback."
        ),
        "target_node": "auth-service",
    },
}

FALLBACK_TIER_2 = FALLBACK_CONTRACT_D


def query_local_llm(
    context: Union[Dict[str, Any], str],
    fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Query local Ollama instance for reasoning with graceful fallback.

    Args:
        context: Context dictionary or prompt string.
        fallback: Optional explicit mock response to return if LLM is unreachable.

    Returns:
        Dict adhering to Contract C / D schema.
    """
    if isinstance(context, str):
        prompt_string = context
        if fallback is None:
            if "tier_1" in prompt_string.lower():
                fallback = FALLBACK_TIER_1
            else:
                fallback = FALLBACK_CONTRACT_D
    elif isinstance(context, dict) and "prompt" in context and isinstance(context["prompt"], str):
        prompt_string = context["prompt"]
        if fallback is None:
            if "tier_1" in prompt_string.lower():
                fallback = FALLBACK_TIER_1
            else:
                fallback = FALLBACK_CONTRACT_D
    else:
        prompt_string = (
            "You are an autonomous air-gapped site reliability engineering agent.\n"
            "Evaluate the following incident telemetry and graph context to determine the remediation action.\n\n"
            f"Context:\n{json.dumps(context, indent=2)}\n\n"
            "Output ONLY a valid JSON object matching the following schema (Contract D):\n"
            "{\n"
            '  "action_type": "tier_2_remediation",\n'
            '  "payload": {\n'
            '    "command": "<str>",\n'
            '    "justification": "<str>",\n'
            '    "target_node": "<str>"\n'
            "  }\n"
            "}\n"
        )
        if fallback is None:
            fallback = FALLBACK_CONTRACT_D

    ollama_payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt_string,
        "stream": False,
        "format": "json",
    }

    try:
        data_bytes = json.dumps(ollama_payload).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_GENERATE_URL,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw_response = result.get("response", "{}")
            parsed_decision = json.loads(raw_response)
            return parsed_decision
    except Exception as e:
        logger.warning("Local LLM unreachable, falling back to mock schema.")
        return fallback if fallback is not None else FALLBACK_CONTRACT_D
