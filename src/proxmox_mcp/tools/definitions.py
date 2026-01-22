"""
Tool descriptions for Proxmox MCP tools.
"""

# Node tool descriptions
GET_NODES_DESC = """List all nodes in the Proxmox cluster with their status, CPU, memory, and role information.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')

Example:
{"node": "pve1", "status": "online", "cpu_usage": 0.15, "memory": {"used": "8GB", "total": "32GB"}}"""

GET_NODE_STATUS_DESC = """Get detailed status information for a specific Proxmox node.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')
node* - Name/ID of node to query (e.g. 'pve1')

Example:
{"cpu": {"usage": 0.15}, "memory": {"used": "8GB", "total": "32GB"}}"""

# VM tool descriptions
GET_VMS_DESC = """List all virtual machines across the cluster with their status and resource usage.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')

Example:
{"vmid": "100", "name": "ubuntu", "status": "running", "cpu": 2, "memory": 4096}"""

EXECUTE_VM_COMMAND_DESC = """Execute commands in a VM via QEMU guest agent.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')
command* - Shell command to run (e.g. 'uname -a')

Example:
{"success": true, "output": "Linux vm1 5.4.0", "exit_code": 0}"""

# Container tool descriptions
GET_CONTAINERS_DESC = """List all LXC containers across the cluster with their status and configuration.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')

Example:
{"vmid": "200", "name": "nginx", "status": "running", "template": "ubuntu-20.04"}"""

# Storage tool descriptions
GET_STORAGE_DESC = """List storage pools across the cluster with their usage and configuration.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')

Example:
{"storage": "local-lvm", "type": "lvm", "used": "500GB", "total": "1TB"}"""

# Cluster tool descriptions
GET_CLUSTER_STATUS_DESC = """Get overall Proxmox cluster health and configuration status.

Parameters:
cluster* - Cluster name (e.g. 'Building 4', 'Building 1-ABE')

Example:
{"name": "proxmox", "quorum": "ok", "nodes": 3, "ha_status": "active"}"""

# List clusters tool description
LIST_CLUSTERS_DESC = """List all configured Proxmox clusters.

Returns a list of available cluster names that can be used with other tools.

Example:
["Building 1-ABE", "Building 2", "Building 3", "Building 4"]"""
