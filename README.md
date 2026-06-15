# 🚀 Proxmox Manager — Proxmox MCP Server

A Python-based [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for
interacting with Proxmox hypervisors. It gives an AI assistant (Claude Code, Claude Desktop,
Cline, …) a clean, token-authenticated interface to **multiple Proxmox clusters** — listing
nodes/VMs/storage, checking cluster health, and running commands inside VMs.

> This is a fork of [canvrno/ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) with:
> - **Multi-cluster support** — manage many Proxmox clusters from one server (every tool takes a `cluster` argument; `list_clusters` discovers them).
> - **Claude Code integration** — first-class `claude mcp add` setup.
> - **Ansible Claude-analysis playbook** — collect metrics across all clusters via the MCP and have Claude write an infrastructure report.

## 🏗️ Built With

- [Proxmoxer](https://github.com/proxmoxer/proxmoxer) — Python wrapper for the Proxmox API
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) — FastMCP server
- [Pydantic](https://docs.pydantic.dev/) — config validation

## ✨ Features

- 🌐 **Multi-cluster**: one server, N clusters, selected per-call by name
- 🔒 Secure token-based authentication (per cluster)
- 🖥️ Tools for nodes, VMs, storage, and cluster status
- 💻 VM command execution via the QEMU guest agent
- 🤖 Ansible playbook that turns live metrics into a Claude-written report
- 🎨 Rich, themed output formatting
- ✅ Type-safe (Pydantic) with a test suite

## 📦 Installation

```bash
git clone https://github.com/bill-mccormick-dg/ProxmoxMCP.git
cd ProxmoxMCP

python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

> Note: this fork uses `venv/` (not `.venv/`).

### Configuration (multi-cluster)

Real credentials live in `proxmox-config/config.json`, which is **gitignored** — never commit
it. Copy the example and fill in one block per cluster:

```bash
cp proxmox-config/config.example.json proxmox-config/config.json
```

`config.example.json` shows a real-world multi-cluster wiring (one block per building), with
every secret/host left as a `REPLACE_WITH_*` placeholder:

```json
{
  "clusters": [
    {
      "name": "Building 1",
      "proxmox": { "host": "REPLACE_WITH_IP", "port": 8006, "verify_ssl": false, "service": "PVE" },
      "auth":    { "user": "root@pam", "token_name": "mcp-token", "token_value": "REPLACE_WITH_TOKEN_VALUE" }
    },
    {
      "name": "Building 2",
      "proxmox": { "host": "REPLACE_WITH_IP", "port": 8006, "verify_ssl": false, "service": "PVE" },
      "auth":    { "user": "root@pam", "token_name": "mcp-token", "token_value": "REPLACE_WITH_TOKEN_VALUE" }
    }
  ],
  "logging": { "level": "INFO", "file": "proxmox_mcp.log" }
}
```

Add as many cluster blocks as you have clusters. A legacy single-cluster config (top-level
`proxmox`/`auth` with no `clusters` array) is auto-converted to a one-cluster list named
`default`, so older configs keep working.

> ⚠️ **Never put real tokens in `config.example.json` or any tracked file.** Only
> `config.json` (gitignored) should hold secrets. Rotate any token that lands in git.

### Proxmox API token setup

1. Proxmox web UI → *Datacenter → Permissions → API Tokens*
2. Create a token (e.g. user `root@pam`, token id `mcp-token`); uncheck "Privilege Separation" for full access
3. Copy the **token id** (`token_name`) and **secret** (`token_value`) into `config.json`

## 🚀 Running

```bash
source venv/bin/activate
PROXMOX_MCP_CONFIG=proxmox-config/config.json python -m proxmox_mcp.server
```

### Claude Code

```bash
claude mcp add proxmox -s user \
  -e PYTHONPATH=/abs/path/ProxmoxMCP/src \
  -e PROXMOX_MCP_CONFIG=/abs/path/ProxmoxMCP/proxmox-config/config.json \
  -- /abs/path/ProxmoxMCP/venv/bin/python -m proxmox_mcp.server

claude mcp list   # expect: proxmox ✔ Connected
```

### Cline / Claude Desktop

Add an `mcpServers` entry (copy `.mcp.json.example` and fill in absolute paths):

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "/abs/path/ProxmoxMCP/venv/bin/python",
      "args": ["-m", "proxmox_mcp.server"],
      "cwd": "/abs/path/ProxmoxMCP",
      "env": {
        "PYTHONPATH": "/abs/path/ProxmoxMCP/src",
        "PROXMOX_MCP_CONFIG": "/abs/path/ProxmoxMCP/proxmox-config/config.json"
      }
    }
  }
}
```

## 🔧 Available Tools

Every cluster-scoped tool takes a **`cluster`** argument — call `list_clusters` first to get the
valid names.

| Tool | Args | Purpose |
|------|------|---------|
| `list_clusters` | — | List configured cluster names. **Call this first.** |
| `get_nodes` | `cluster` | Nodes in a cluster with status, CPU, memory |
| `get_node_status` | `cluster`, `node` | Detailed status for one node |
| `get_vms` | `cluster` | All VMs with status and resource usage |
| `get_storage` | `cluster` | Storage pools with usage |
| `get_cluster_status` | `cluster` | Overall cluster health / quorum |
| `execute_vm_command` | `cluster`, `node`, `vmid`, `command` | Run a command in a VM via QEMU guest agent |

`execute_vm_command` requires the VM to be running with the QEMU guest agent installed and
command execution enabled.

## 🤖 Ansible: Claude-powered analysis

`ansible/proxmox-analysis.yml` collects metrics from **every** configured cluster (via the MCP,
not by hitting the Proxmox API directly — see `ansible/proxmox_mcp_query.py`) and asks Claude to
write a Markdown infrastructure report into `ansible/reports/`.

Two backends (set `analysis_backend` in the playbook):
- **`cli`** (default) — uses the local `claude` CLI / your Claude.ai subscription (no API credits)
- **`api`** — POSTs to `api.anthropic.com`; needs `ansible/vars/anthropic.yml` (ansible-vault encrypted, gitignored) with `anthropic_api_key`

```bash
export PROXMOX_MCP_CONFIG=$PWD/proxmox-config/config.json

# CLI backend (subscription)
ansible-playbook ansible/proxmox-analysis.yml

# API backend
cp ansible/vars/anthropic.yml.example ansible/vars/anthropic.yml   # add key, then:
ansible-vault encrypt ansible/vars/anthropic.yml
ansible-playbook ansible/proxmox-analysis.yml -e analysis_backend=api --ask-vault-pass
```

## 👨‍💻 Development

```bash
source venv/bin/activate
pytest        # tests
black .       # format
ruff .        # lint
mypy .        # type check
```

See `CLAUDE.md` for an architecture overview.

## 📁 Project Structure

```
ProxmoxMCP/
├── src/proxmox_mcp/
│   ├── server.py            # FastMCP server, tool registration, entry point
│   ├── config/              # loader + Pydantic models (multi-cluster)
│   ├── core/                # ProxmoxClusterManager (N cluster connections), logging
│   ├── formatting/          # themed output
│   └── tools/               # node / vm / storage / cluster / console tools
├── ansible/
│   ├── proxmox-analysis.yml # collect metrics across clusters → Claude report
│   ├── proxmox_mcp_query.py # CLI wrapper that calls MCP tools, emits JSON
│   ├── vars/                # anthropic.yml (vault, gitignored) + .example
│   └── reports/             # generated reports (gitignored)
├── proxmox-config/
│   ├── config.json          # YOUR clusters + tokens (gitignored — never commit)
│   └── config.example.json  # real-world multi-cluster example (placeholders only)
├── CLAUDE.md
└── pyproject.toml
```

## 📄 License

MIT License
