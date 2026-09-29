"""Ollama LLM Agent bridging Qwen 2.5 Coder to SovereignOps MCP Server.

Connects the local `qwen2.5-coder:7b` model (via the `ollama` Python SDK) to our MCP server
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
                "Follow this sequence: (1) Use list_services to find available services. "
                "(2) Use get_diagnostic_logs to fetch relevant logs. If a log indicates an upstream error, "
                "fetch the upstream service's logs. (3) Use list_runbooks and get_runbook to find the remediation. "
                "(4) Use execute_k8s_rollback to apply the fix. Once the rollback succeeds, output "
                "\"FINAL REMEDIATION PLAN:\" followed by a brief summary."
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
            tools_used: set[str] = set()  # Tracks executed tools for ordered guard checks
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

                if "FINAL REMEDIATION PLAN" in response_text.upper():
                    print("[+] Remediation plan detected. Halting agent loop.")
                    break

                # --- GUARD 1: Multi-tool hallucination detection ---
                all_calls = extract_all_tool_calls(response_msg)    

                # Append assistant message to cumulative conversation history
                messages.append(response_msg)

                if content:
                    print(f"\n[Thought / Response]:\n{content}")

                if len(all_calls) > 1:
                    # LLM tried to invoke multiple tools in one shot — reject all of them
                    detected = ", ".join(f"'{n}'" for n, _ in all_calls)
                    obs_text = (
                        "Error: You attempted to call multiple tools at once "
                        f"({detected}). You must output EXACTLY ONE tool call per response."
                    )
                    print(f"\n[!] Multi-tool hallucination detected: {detected}")
                    print(f"[Observe]:\n{obs_text}")
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
                    elif tool_name == "execute_k8s_rollback" and "get_runbook" not in tools_used:
                        obs_text = (
                            "Error: CRITICAL SAFETY RULE VIOLATION. You must call "
                            "'get_runbook' before executing any remediations."
                        )

                    if obs_text:
                        # State machine guard fired — inject error, do NOT execute
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
                    tools_used.add(tool_name)  # Register successful execution
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
    asyncio.run(run_qwen_mcp_agent())
