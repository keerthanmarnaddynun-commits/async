"""Ollama LLM Agent bridging Llama 3.1 to SovereignOps MCP Server.

Connects the local `llama3.1` model (via the `ollama` Python SDK) to our MCP server
over stdio transport, enabling autonomous tool discovery and execution.
"""

import sys
import json
import time
import asyncio
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


async def run_ollama_mcp_agent():
    """Execute Ollama Llama 3.1 agent loop connected to SovereignOps MCP server."""
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
            executed_tools = set()

            print("\n[*] Discovering tools registered on MCP Server...")
            tools_result = await session.list_tools()
            mapped_tools = [map_mcp_tool_to_ollama(tool) for tool in tools_result.tools]

            print(f"[+] Mapped {len(mapped_tools)} tools for Ollama llama3.1:")
            for tool in mapped_tools:
                print(f"    - {tool['function']['name']}: {tool['function']['description'].splitlines()[0]}")

            # 2. ReAct System Prompt & Initial User Prompt
            system_prompt = (
                "You are an autonomous SRE agent. You must use the ReAct framework. "
                "You may only invoke ONE tool at a time. "
                "After invoking a tool, STOP and wait for the observation result before taking your next action. "
                "You must follow this investigation sequence: "
                "(1) Use list_services to discover what services exist on the node. "
                "(2) Use get_diagnostic_logs to fetch the relevant gateway service logs. If those logs indicate an error or timeout from a specific upstream service, you MUST invoke get_diagnostic_logs a second time to read the logs of that specific upstream service before proceeding. "
                "(3) Use list_runbooks to discover available runbooks and find the correct runbook ID for the incident. "
                "(4) Use get_runbook with the correct ID to read the remediation instructions. "
                "(5) ONLY THEN use execute_k8s_rollback to apply the fix. "
                "Once you have completed all steps, provide your FINAL REMEDIATION PLAN. "
                "CRITICAL SAFETY RULE: You are strictly forbidden from using any remediation or execution tools "
                "(such as execute_k8s_rollback) until you have explicitly called get_runbook and read the instructions. "
                "You must observe the environment, read the runbook, and ONLY THEN execute a fix. "
                "Once the rollback succeeds, you must output \"FINAL REMEDIATION PLAN:\" followed by a summary, and you MUST NOT output any further JSON tool calls."
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
            start_time = time.time()

            while True:
                iteration += 1
                if iteration > max_iterations:
                    print(f"\n[!] Safeguard reached (max_iterations={max_iterations}). Halting agent loop.")
                    break

                print(f"\n" + "-" * 40)
                print(f"[*] [Iteration {iteration}] Sending conversation history to Ollama (llama3.1)...")
                messages[:] = sliding_window_messages(messages, max_turns=3)
                try:
                    response = ollama.chat(
                        model="llama3.1",
                        messages=messages,
                        tools=mapped_tools,
                    )
                except Exception as exc:
                    print(f"[-] Ollama chat query failed: {exc}")
                    print("[-] Ensure Ollama server is running locally with 'llama3.1' model installed.")
                    elapsed_time = time.time() - start_time
                    print(f"[+] Total execution time: {elapsed_time:.2f} seconds")
                    return

                response_msg = response.get("message", {})
                content = response_msg.get("content", "")
                response_text = content or ""

                if "FINAL REMEDIATION PLAN" in response_text.upper():
                    print("[+] Remediation plan detected. Halting agent loop.")
                    break

                # --- Smart Filter & Deduplicator ---
                llm_json_array = extract_all_tool_calls(response_msg)

                # Append assistant message to cumulative conversation history
                messages.append(response_msg)

                if content:
                    print(f"\n[Thought / Response]:\n{content}")

                if llm_json_array:
                    selected_tool = None
                    selected_args = None
                    for proposed_tool in llm_json_array:
                        tool_name, tool_args = proposed_tool
                        if tool_name in executed_tools:
                            print(f"[*] Skipping repeated tool: {tool_name}")
                            continue
                        selected_tool = tool_name
                        selected_args = tool_args
                        executed_tools.add(tool_name)
                        break

                    if selected_tool is None:
                        retry_msg = (
                            "SYSTEM: All suggested tools were already executed. "
                            "Please analyze the observations and propose a NEW action."
                        )
                        print(f"\n[!] {retry_msg}")
                        messages.append({"role": "system", "content": retry_msg})
                        continue

                    tool_name, tool_args = selected_tool, selected_args

                    # --- State machine — ordered prerequisite enforcement ---
                    obs_text = None  # Will be set if a guard fires

                    if tool_name == "get_runbook" and "get_diagnostic_logs" not in executed_tools:
                        obs_text = (
                            "Error: State Machine Violation. You must call "
                            "'get_diagnostic_logs' to investigate the issue before requesting a runbook. "
                            "You may also call 'list_runbooks' at any time to discover available runbook IDs."
                        )
                    elif tool_name == "execute_k8s_rollback" and "get_runbook" not in executed_tools:
                        obs_text = (
                            "Error: CRITICAL SAFETY RULE VIOLATION. You must call "
                            "'get_runbook' before executing any remediations."
                        )

                    if obs_text:
                        # State machine guard fired — inject error, do NOT execute
                        executed_tools.discard(tool_name)
                        print(f"\n[!] State machine blocked '{tool_name}': {obs_text}")
                        print(f"[Observe]:\n{obs_text}")
                        messages.append({"role": "user", "content": f"Observation: {obs_text}"})
                        continue

                    # --- Execute the validated, single tool call ---
                    print(f"\n[Act] Invoking single MCP Tool: '{tool_name}'")
                    print(f"      Arguments: {json.dumps(tool_args)}")

                    result = await session.call_tool(tool_name, arguments=tool_args)

                    content_text = ""
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            content_text += content_item.text + "\n"
                        else:
                            content_text += str(content_item) + "\n"

                    content_text = content_text.strip()
                    print(f"\n[Observe]:\n{content_text}")

                    messages.append({"role": "user", "content": f"Observation: {content_text}"})

                else:
                    # No tool call found — LLM is producing its final answer
                    print("\n" + "=" * 60)
                    print("[+] FINAL REMEDIATION PLAN / REASONING:")
                    print("=" * 60)
                    print(content)
                    break

            elapsed_time = time.time() - start_time
            print(f"[+] Total execution time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(run_ollama_mcp_agent())
