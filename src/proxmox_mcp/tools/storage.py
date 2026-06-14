"""
Storage-related tools for Proxmox MCP.

This module provides tools for managing and monitoring Proxmox storage:
- Listing all storage pools across the cluster
- Retrieving detailed storage information including:
  * Storage type and content types
  * Usage statistics and capacity
  * Availability status
  * Node assignments

The tools implement fallback mechanisms for scenarios where
detailed storage information might be temporarily unavailable.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_STORAGE_DESC

class StorageTools(ProxmoxTool):
    """Tools for managing Proxmox storage.
    
    Provides functionality for:
    - Retrieving cluster-wide storage information
    - Monitoring storage pool status and health
    - Tracking storage utilization and capacity
    - Managing storage content types
    
    Implements fallback mechanisms for scenarios where detailed
    storage information might be temporarily unavailable.
    """

    def _collect_storage_usage(self, api) -> dict:
        """Build a {storage_name: {used, total, avail}} map from all online nodes.

        The cluster-wide /storage endpoint only lists pool definitions; usage
        figures are reported per node at /nodes/{node}/storage. Iterating the
        online nodes lets us populate usage for both local pools (reported only
        on their owning node) and shared pools (reported identically on every
        node). The first node reporting a non-zero total wins for each pool.
        """
        usage: dict = {}
        try:
            nodes = api.nodes.get()
        except Exception:
            return usage

        for node in nodes:
            node_name = node.get("node")
            if not node_name or node.get("status") != "online":
                continue
            try:
                node_storage = api.nodes(node_name).storage.get()
            except Exception:
                continue
            for s in node_storage:
                name = s.get("storage")
                if not name:
                    continue
                total = s.get("total", 0)
                # Keep the first entry that actually reports capacity so a node
                # where the pool is inactive (total 0) doesn't mask a good one.
                if name not in usage or (total and not usage[name].get("total")):
                    usage[name] = {
                        "used": s.get("used", 0),
                        "total": total,
                        "avail": s.get("avail", 0),
                    }
        return usage

    def get_storage(self, cluster: str) -> List[Content]:
        """List storage pools across a cluster with detailed status.

        Retrieves comprehensive information for each storage pool including:
        - Basic identification (name, type)
        - Content types supported (VM disks, backups, ISO images, etc.)
        - Availability status (online/offline)
        - Usage statistics:
          * Used space
          * Total capacity
          * Available space

        Implements a fallback mechanism that returns basic information
        if detailed status retrieval fails for any storage pool.

        Args:
            cluster: Name of the cluster to query (e.g., 'Building 4')

        Returns:
            List of Content objects containing formatted storage information

        Raises:
            ValueError: If the cluster name is not found
            RuntimeError: If the cluster-wide storage query fails
        """
        try:
            api = self.get_api(cluster)
            result = api.storage.get()

            # Usage statistics are exposed per node via /nodes/{node}/storage,
            # not on the cluster-wide /storage endpoint. Build a usage map by
            # querying each online node; a pool's stats are taken from the first
            # node that reports a non-zero total (shared pools report identical
            # numbers on every node, local pools only on their owning node).
            usage = self._collect_storage_usage(api)

            storage = []
            for store in result:
                name = store["storage"]
                stats = usage.get(name, {})
                storage.append({
                    "storage": name,
                    "type": store["type"],
                    "content": store.get("content", []),
                    "status": "online" if store.get("enabled", True) else "offline",
                    "used": stats.get("used", 0),
                    "total": stats.get("total", 0),
                    "available": stats.get("avail", 0),
                })

            return self._format_response(storage, "storage")
        except ValueError:
            raise
        except Exception as e:
            self._handle_error("get storage", e)
