"""Ollama LLM Agent bridging Qwen 2.5 Coder to SovereignOps MCP Server.

Connects the local `qwen2.5-coder:7b` model (via the `ollama` Python SDK) to our MCP server
over stdio transport, enabling autonomous tool discovery and execution.
"""

import sys
import json
import time
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

import ollama
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def map_mcp_tool_to_ollama(tool) -> dict:
    """Convert an MCP Tool definition into the Ollama function tool JSON schema."""
    input_schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", {}))
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": input_schema,
        },
    }


def extract_all_tool_calls(response_msg) -> list[tuple[str, dict]]:
    """Extract ALL tool calls from a response — used to detect multi-tool hallucinations.

    Returns a list of (tool_name, args) tuples. An empty list means no tool call
    was found (LLM is producing a final answer). More than one entry signals a
    hallucination that the state machine must reject.
    """
    # --- Native Ollama structured tool_calls ---
    native = response_msg.get("tool_calls", [])
    if native:
        results = []
        for tc in native:
            func = tc.get("function", {})
            results.append((func.get("name", ""), func.get("arguments", {})))
        return results

    # --- Regex fallback for unstructured text output ---
    content = response_msg.get("content", "")
    if not content:
        return []

    import re
    patterns = [
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"parameters"\s*:\s*(\{.*?\})\s*\}',
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*\}',
    ]
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.DOTALL):
            tool_name = match.group(1)
            args_str = match.group(2) if match.lastindex >= 2 else "{}"
            try:
                args = json.loads(args_str)
            except Exception:
                args = {}
            found.append((tool_name, args))
        if found:
            # Use whichever pattern produced results; don't double-count
            break

    return found


def sliding_window_messages(messages: list, max_turns: int = 3) -> list:
    """Keep the system + user prompts and only the most recent ReAct turns.

    A turn is an assistant response paired with the following tool observation.
    Older turns are dropped so the Ollama payload stays bounded.
    """
    if len(messages) <= 2:
        return messages
    prefix = messages[:2]
    history = messages[2:]
    max_history = max_turns * 2
    if len(history) > max_history:
        history = history[-max_history:]
    return prefix + history


def create_sse_event(
    event_type: str,
    payload: dict,
    iteration: int = 1,
    incident_id: str = "INC-8891",
) -> dict:
    """Wrap event payload in the standardized base SSE event schema matching Frontend Data Contract."""
    return {
        "event_id": str(uuid.uuid4()),
        "incident_id": incident_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "iteration": iteration,
        "payload": payload,
    }


def emit_event(event_type: str, payload: dict, iteration: int = 1, incident_id: str = "INC-8891") -> dict:
    """Emit standardized SSE JSON event to stdout stream."""
    event_dict = create_sse_event(event_type, payload, iteration, incident_id)
    print(f"\n[EVENT] {json.dumps(event_dict)}", flush=True)
    return event_dict


async def run_qwen_mcp_agent():
    """Execute Ollama Qwen 2.5 Coder agent loop connected to SovereignOps MCP server."""
    server_script = Path(__file__).resolve().parent / "server.py"

    print(f"[*] Spawning MCP Server process: {server_script}")

    # Configure stdio server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=None,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Handshake & Tool Discovery
            print("[*] Initializing MCP session handshake...")
            await session.initialize()
            print("[+] Session initialized successfully.")

            print("\n[*] Discovering tools registered on MCP Server...")
            tools_result = await session.list_tools()
            mapped_tools = [map_mcp_tool_to_ollama(tool) for tool in tools_result.tools]

            print(f"[+] Mapped {len(mapped_tools)} tools for Ollama qwen2.5-coder:7b:")
            for tool in mapped_tools:
                print(f"    - {tool['function']['name']}: {tool['function']['description'].splitlines()[0]}")

            # 2. ReAct System Prompt & Initial User Prompt
            system_prompt = (
                "You are an autonomous SRE agent. You must use the ReAct framework "
                "(Thought/Action/Observation). You may only invoke ONE tool at a time. "
                "After invoking a tool, wait for the observation result before taking your next action. "
                "Follow this strict Standard Operating Procedure (SOP):\n"
                "- Step 1: Diagnose the alert using logs (get_diagnostic_logs).\n"
                "- Step 2: Trace the fault using the graph (query_infrastructure_graph).\n"
                "- Step 3: Validate historical fixes using memory (search_provenance_memory).\n"
                "- Step 4: Execute remediation (e.g., execute_k8s_rollback) ONLY after memory validation is complete.\n"
                "Once the rollback succeeds, output \"FINAL REMEDIATION PLAN:\" followed by a brief summary."
            )

            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        "The system is throwing a 503 error on node 'api-gateway-01'. "
                        "Figure out what services are available on the node, "
                        "fetch the logs for the relevant failing gateway service, "
                        "find the correct runbook for the issue, "
                        "and figure out how to fix it."
                    ),
                },
            ]

            print("\n" + "=" * 60)
            print(f"[*] System Prompt: {system_prompt}")
            print(f"[*] User Prompt: {messages[1]['content']}")
            print("=" * 60)

            # 3. Strict ReAct State Machine (Reason -> Act -> Observe)
            max_iterations = 10
            iteration = 0
            incident_id = "INC-8891"
            triggering_service = "api-gateway-01"
            tools_used: set[str] = set()
            has_verified_memory = False
            guardrail_interventions_count = 0
            traced_root_cause_data: dict = {}
            matched_runbook_data: dict = {}
            action_taken_str: str = "None"
            final_summary_text: str = ""
            start_time = time.time()

            while True:
                iteration += 1
                if iteration > max_iterations:
                    print(f"\n[!] Safeguard reached (max_iterations={max_iterations}). Halting agent loop.")
                    break

                print(f"\n" + "-" * 40)
                print(f"[*] [Iteration {iteration}] Sending conversation history to Ollama (qwen2.5-coder:7b)...")
                messages[:] = sliding_window_messages(messages, max_turns=3)
                try:
                    response = ollama.chat(
                        model="qwen2.5-coder:7b",
                        messages=messages,
                        tools=mapped_tools,
                    )
                except Exception as exc:
                    print(f"[-] Ollama chat query failed: {exc}")
                    print("[-] Ensure Ollama server is running locally with 'qwen2.5-coder:7b' model installed.")
                    elapsed_time = time.time() - start_time
                    print(f"[+] Total execution time: {elapsed_time:.2f} seconds")
                    return

                response_msg = response.get("message", {})
                content = response_msg.get("content", "")
                response_text = content or ""

                if content:
                    print(f"\n[Thought / Response]:\n{content}")
                    emit_event(
                        "agent_thought",
                        {
                            "phase": "REASONING",
                            "thought_content": content,
                            "model": "qwen2.5-coder:7b",
                            "sliding_window_turns": 3,
                        },
                        iteration=iteration,
                        incident_id=incident_id,
                    )

                if "FINAL REMEDIATION PLAN" in response_text.upper():
                    print("[+] Remediation plan detected. Halting agent loop.")
                    final_summary_text = response_text
                    break

                # --- GUARD 1: Multi-tool hallucination detection ---
                all_calls = extract_all_tool_calls(response_msg)    

                # Append assistant message to cumulative conversation history
                messages.append(response_msg)

                if len(all_calls) > 1:
                    # LLM tried to invoke multiple tools in one shot — reject all of them
                    detected = ", ".join(f"'{n}'" for n, _ in all_calls)
                    obs_text = (
                        "Error: You attempted to call multiple tools at once "
                        f"({detected}). You must output EXACTLY ONE tool call per response."
                    )
                    print(f"\n[!] Multi-tool hallucination detected: {detected}")
                    print(f"[Observe]:\n{obs_text}")
                    guardrail_interventions_count += 1
                    emit_event(
                        "guardrail_intervention",
                        {
                            "guardrail_type": "multi_tool_hallucination",
                            "policy_rule": "Agent must invoke exactly one tool per ReAct iteration.",
                            "attempted_action": {"tool_calls": [n for n, _ in all_calls]},
                            "intervention_action": "BLOCKED",
                            "corrective_guidance": obs_text,
                        },
                        iteration=iteration,
                        incident_id=incident_id,
                    )
                    messages.append({"role": "user", "content": f"Observation: {obs_text}"})
                    continue

                if len(all_calls) == 1:
                    tool_name, tool_args = all_calls[0]

                    # --- GUARD 2: State machine — ordered prerequisite enforcement ---
                    obs_text = None  # Will be set if a guard fires

                    if tool_name == "get_runbook" and "get_diagnostic_logs" not in tools_used:
                        obs_text = (
                            "Error: State Machine Violation. You must call "
                            "'get_diagnostic_logs' to investigate the issue before requesting a runbook. "
                            "You may also call 'list_runbooks' at any time to discover available runbook IDs."
                        )
                        guardrail_interventions_count += 1
                        emit_event(
                            "guardrail_intervention",
                            {
                                "guardrail_type": "state_machine_prerequisite_violation",
                                "policy_rule": "Must inspect diagnostic logs before requesting runbook.",
                                "attempted_action": {"tool_name": tool_name},
                                "intervention_action": "BLOCKED",
                                "corrective_guidance": obs_text,
                            },
                            iteration=iteration,
                            incident_id=incident_id,
                        )
                    elif tool_name == "execute_k8s_rollback" and not has_verified_memory:
                        corrective_guidance = (
                            "Execution intercepted by Caged ReAct Guardrail. Call 'search_provenance_memory' "
                            "to verify historical post-mortem fix confidence before attempting rollout undo."
                        )
                        guardrail_interventions_count += 1
                        emit_event(
                            "guardrail_intervention",
                            {
                                "guardrail_type": "state_machine_prerequisite_violation",
                                "policy_rule": "CRITICAL SAFETY RULE: Agent must query Provenance Memory before executing destructive remediation actions.",
                                "attempted_action": {
                                    "tool_name": "execute_k8s_rollback"
                                },
                                "intervention_action": "BLOCKED",
                                "corrective_guidance": corrective_guidance,
                            },
                            iteration=iteration,
                            incident_id=incident_id,
                        )
                        obs_text = corrective_guidance

                    if obs_text:
                        # State machine guard fired — inject error, do NOT execute
                        print(f"\n[!] State machine blocked '{tool_name}': {obs_text}")
                        print(f"[Observe]:\n{obs_text}")
                        messages.append({"role": "user", "content": f"Observation: {obs_text}"})
                        continue

                    # --- Execute the validated, single tool call ---
                    print(f"\n[Act] Invoking single MCP Tool: '{tool_name}'")
                    print(f"      Arguments: {json.dumps(tool_args)}")

                    tool_start_time = time.time()
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    tool_end_time = time.time()
                    execution_latency_ms = round((tool_end_time - tool_start_time) * 1000, 2)

                    content_text = ""
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            content_text += content_item.text + "\n"
                        else:
                            content_text += str(content_item) + "\n"

                    content_text = content_text.strip()
                    tools_used.add(tool_name)  # Register successful execution

                    try:
                        parsed_output = json.loads(content_text)
                    except Exception:
                        parsed_output = content_text

                    status = "ERROR" if ("Error" in content_text or "failed" in content_text.lower()) else "SUCCESS"

                    if tool_name == "query_infrastructure_graph":
                        tool_source = "infrastructure_graph"
                        if isinstance(parsed_output, dict):
                            traced_root_cause_data = parsed_output.get("traced_root_cause", parsed_output)
                    elif tool_name == "search_provenance_memory":
                        tool_source = "provenance_memory"
                        has_verified_memory = True
                        if isinstance(parsed_output, dict):
                            matched_runbook_data = parsed_output
                    else:
                        tool_source = "mcp_server"
                        if tool_name in ("get_runbook",):
                            has_verified_memory = True
                        if tool_name == "execute_k8s_rollback":
                            action_taken_str = f"execute_k8s_rollback: {tool_args.get('deployment_name', '')}"

                    emit_event(
                        "tool_execution",
                        {
                            "tool_name": tool_name,
                            "tool_source": tool_source,
                            "input_parameters": tool_args,
                            "status": status,
                            "execution_latency_ms": execution_latency_ms,
                            "output": parsed_output,
                        },
                        iteration=iteration,
                        incident_id=incident_id,
                    )

                    print(f"\n[Observe]:\n{content_text}")

                    messages.append({"role": "user", "content": f"Observation: {content_text}"})

                else:
                    # No tool call found — LLM is producing its final answer
                    print("\n" + "=" * 60)
                    print("[+] FINAL REMEDIATION PLAN / REASONING:")
                    print("=" * 60)
                    print(content)
                    final_summary_text = content
                    break

            total_execution_time_sec = round(time.time() - start_time, 2)

            emit_event(
                "resolution",
                {
                    "status": "RESOLVED",
                    "triggering_service": triggering_service,
                    "traced_root_cause": traced_root_cause_data,
                    "matched_runbook": matched_runbook_data,
                    "action_taken": action_taken_str,
                    "summary": final_summary_text,
                    "total_execution_time_sec": total_execution_time_sec,
                    "total_iterations": iteration,
                    "guardrail_interventions_count": guardrail_interventions_count,
                },
                iteration=iteration,
                incident_id=incident_id,
            )

            print(f"[+] Total execution time: {total_execution_time_sec:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(run_qwen_mcp_agent())

