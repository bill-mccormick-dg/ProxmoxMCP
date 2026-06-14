#!/usr/bin/env python3
"""
CLI wrapper that calls ProxmoxMCP tools and returns JSON output.
Used by the Ansible playbook to collect metrics via the MCP server
rather than hitting the Proxmox API directly.

Usage:
  python proxmox_mcp_query.py --config <path> list_clusters
  python proxmox_mcp_query.py --config <path> --cluster <name> get_nodes
  python proxmox_mcp_query.py --config <path> --cluster <name> all
"""
import asyncio
import json
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from proxmox_mcp.server import ProxmoxMCPServer

CLUSTER_TOOLS = [
    "get_nodes",
    "get_vms",
    "get_storage",
    "get_cluster_status",
]


async def run(config_path: str, tool: str, cluster: str | None) -> None:
    server = ProxmoxMCPServer(config_path)

    if tool == "list_clusters":
        clusters = server.cluster_manager.list_clusters()
        print(json.dumps({"clusters": clusters}))
        return

    if not cluster:
        print(json.dumps({"error": f"--cluster is required for tool '{tool}'"}), file=sys.stderr)
        sys.exit(1)

    if tool == "all":
        results = {}
        for tool_name in CLUSTER_TOOLS:
            try:
                result = await server.mcp.call_tool(tool_name, {"cluster": cluster})
                results[tool_name] = result[0].text if result else ""
            except Exception as e:
                results[tool_name] = f"Error: {e}"
        print(json.dumps(results))
        return

    try:
        result = await server.mcp.call_tool(tool, {"cluster": cluster})
        print(json.dumps({"output": result[0].text if result else ""}))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query ProxmoxMCP tools and return JSON")
    parser.add_argument(
        "tool",
        choices=["list_clusters"] + CLUSTER_TOOLS + ["all"],
        help="Tool to call. Use 'all' to collect all metrics for a cluster in one call.",
    )
    parser.add_argument("--config", required=True, help="Path to MCP config JSON file")
    parser.add_argument("--cluster", help="Cluster name (required for all tools except list_clusters)")
    args = parser.parse_args()

    asyncio.run(run(args.config, args.tool, args.cluster))


if __name__ == "__main__":
    main()
