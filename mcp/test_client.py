"""Async test client for SovereignOps MCP Server.

Spawns the MCP server via stdio transport, initializes an MCP ClientSession,
discovers available tools, and invokes all 3 registered tools.
"""

import sys
import asyncio
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run_test_client():
    """Execute stdio MCP client verification workflow."""
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
            # Step 1: Initialize MCP session handshake
            print("[*] Initializing MCP session handshake...")
            await session.initialize()
            print("[+] Session initialized successfully.")

            # Step 2: Tool Discovery
            print("\n[*] Discovering tools registered on server...")
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            print(f"[+] Discovered tools ({len(tool_names)}): {tool_names}")

            for tool in tools_result.tools:
                print(f"    - Name: {tool.name}")
                print(f"      Description: {tool.description.splitlines()[0] if tool.description else ''}")

            # Step 3: Tool Execution - get_diagnostic_logs
            print("\n[*] Invoking tool 'get_diagnostic_logs' (target=api-gateway-01, service=gateway-proxy)...")
            diag_result = await session.call_tool(
                "get_diagnostic_logs",
                arguments={
                    "target_node": "api-gateway-01",
                    "service_name": "gateway-proxy",
                },
            )
            for item in diag_result.content:
                print(getattr(item, "text", item))

            # Step 4: Tool Execution - get_runbook
            print("[*] Invoking tool 'get_runbook' (runbook_id=RB-089)...")
            runbook_result = await session.call_tool(
                "get_runbook",
                arguments={"runbook_id": "RB-089"},
            )
            for item in runbook_result.content:
                print(getattr(item, "text", item))

            # Step 5: Tool Execution - execute_k8s_rollback
            print("\n[*] Invoking tool 'execute_k8s_rollback' (deployment_name=auth-service)...")
            rollback_result = await session.call_tool(
                "execute_k8s_rollback",
                arguments={"deployment_name": "auth-service"},
            )
            for item in rollback_result.content:
                print(getattr(item, "text", item))

            # Step 6: Tool Execution - list_services
            print("\n[*] Invoking tool 'list_services'...")
            services_result = await session.call_tool("list_services", arguments={})
            for item in services_result.content:
                print(getattr(item, "text", item))


if __name__ == "__main__":
    asyncio.run(run_test_client())
