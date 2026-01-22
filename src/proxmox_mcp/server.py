"""
Main server implementation for Proxmox MCP.

This module implements the core MCP server for Proxmox integration, providing:
- Configuration loading and validation
- Logging setup
- Multi-cluster Proxmox API connection management
- MCP tool registration and routing
- Signal handling for graceful shutdown

The server exposes a set of tools for managing Proxmox resources including:
- Node management
- VM operations
- Storage management
- Cluster status monitoring
"""
import logging
import os
import sys
import signal
from typing import Optional, List, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.types import TextContent as Content
from pydantic import Field

from .config.loader import load_config
from .core.logging import setup_logging
from .core.proxmox import ProxmoxClusterManager
from .tools.node import NodeTools
from .tools.vm import VMTools
from .tools.storage import StorageTools
from .tools.cluster import ClusterTools
from .tools.definitions import (
    GET_NODES_DESC,
    GET_NODE_STATUS_DESC,
    GET_VMS_DESC,
    EXECUTE_VM_COMMAND_DESC,
    GET_CONTAINERS_DESC,
    GET_STORAGE_DESC,
    GET_CLUSTER_STATUS_DESC,
    LIST_CLUSTERS_DESC
)

class ProxmoxMCPServer:
    """Main server class for Proxmox MCP."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the server.

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config.logging)

        # Initialize cluster manager with all configured clusters
        self.cluster_manager = ProxmoxClusterManager(self.config.clusters)

        # Initialize tools with cluster manager
        self.node_tools = NodeTools(self.cluster_manager)
        self.vm_tools = VMTools(self.cluster_manager)
        self.storage_tools = StorageTools(self.cluster_manager)
        self.cluster_tools = ClusterTools(self.cluster_manager)

        # Initialize MCP server
        self.mcp = FastMCP("ProxmoxMCP")
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Register MCP tools with the server.

        Initializes and registers all available tools with the MCP server:
        - Cluster listing tool
        - Node management tools (list nodes, get status)
        - VM operation tools (list VMs, execute commands)
        - Storage management tools (list storage)
        - Cluster tools (get cluster status)

        Each tool is registered with appropriate descriptions and parameter
        validation using Pydantic models. All tools require a cluster parameter
        to specify which Proxmox cluster to target.
        """

        # List clusters tool
        @self.mcp.tool(description=LIST_CLUSTERS_DESC)
        def list_clusters():
            clusters = self.cluster_manager.list_clusters()
            return [Content(type="text", text=f"Available clusters: {', '.join(clusters)}")]

        # Node tools
        @self.mcp.tool(description=GET_NODES_DESC)
        def get_nodes(
            cluster: Annotated[str, Field(description="Cluster name (e.g. 'Building 4', 'Building 1-ABE')")]
        ):
            return self.node_tools.get_nodes(cluster)

        @self.mcp.tool(description=GET_NODE_STATUS_DESC)
        def get_node_status(
            cluster: Annotated[str, Field(description="Cluster name (e.g. 'Building 4', 'Building 1-ABE')")],
            node: Annotated[str, Field(description="Name/ID of node to query (e.g. 'pve1', 'proxmox-node2')")]
        ):
            return self.node_tools.get_node_status(cluster, node)

        # VM tools
        @self.mcp.tool(description=GET_VMS_DESC)
        def get_vms(
            cluster: Annotated[str, Field(description="Cluster name (e.g. 'Building 4', 'Building 1-ABE')")]
        ):
            return self.vm_tools.get_vms(cluster)

        @self.mcp.tool(description=EXECUTE_VM_COMMAND_DESC)
        async def execute_vm_command(
            cluster: Annotated[str, Field(description="Cluster name (e.g. 'Building 4', 'Building 1-ABE')")],
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1', 'proxmox-node2')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100', '101')")],
            command: Annotated[str, Field(description="Shell command to run (e.g. 'uname -a', 'systemctl status nginx')")]
        ):
            return await self.vm_tools.execute_command(cluster, node, vmid, command)

        # Storage tools
        @self.mcp.tool(description=GET_STORAGE_DESC)
        def get_storage(
            cluster: Annotated[str, Field(description="Cluster name (e.g. 'Building 4', 'Building 1-ABE')")]
        ):
            return self.storage_tools.get_storage(cluster)

        # Cluster tools
        @self.mcp.tool(description=GET_CLUSTER_STATUS_DESC)
        def get_cluster_status(
            cluster: Annotated[str, Field(description="Cluster name (e.g. 'Building 4', 'Building 1-ABE')")]
        ):
            return self.cluster_tools.get_cluster_status(cluster)

    def start(self) -> None:
        """Start the MCP server.
        
        Initializes the server with:
        - Signal handlers for graceful shutdown (SIGINT, SIGTERM)
        - Async runtime for handling concurrent requests
        - Error handling and logging
        
        The server runs until terminated by a signal or fatal error.
        """
        import anyio

        def signal_handler(signum, frame):
            self.logger.info("Received signal to shutdown...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.logger.info("Starting MCP server...")
            anyio.run(self.mcp.run_stdio_async)
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    config_path = os.getenv("PROXMOX_MCP_CONFIG")
    if not config_path:
        print("PROXMOX_MCP_CONFIG environment variable must be set")
        sys.exit(1)
    
    try:
        server = ProxmoxMCPServer(config_path)
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
