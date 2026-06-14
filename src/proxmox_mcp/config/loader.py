"""
Configuration loading utilities for the Proxmox MCP server.

This module handles loading and validation of server configuration:
- JSON configuration file loading
- Multi-cluster configuration support
- Legacy single-cluster config conversion
- Configuration validation using Pydantic models
- Error handling for invalid configurations

The module ensures that all required configuration is present
and valid before the server starts operation.
"""
import json
import os
from typing import Optional
from .models import Config

def _convert_legacy_config(config_data: dict) -> dict:
    """Convert legacy single-cluster config to new multi-cluster format.

    Legacy format:
        {
            "proxmox": {...},
            "auth": {...},
            "logging": {...}
        }

    New format:
        {
            "clusters": [{"name": "default", "proxmox": {...}, "auth": {...}}],
            "logging": {...}
        }
    """
    return {
        "clusters": [{
            "name": "default",
            "proxmox": config_data["proxmox"],
            "auth": config_data["auth"]
        }],
        "logging": config_data.get("logging", {"level": "INFO"})
    }

def _validate_cluster_names(config_data: dict) -> None:
    """Validate that all cluster names are unique."""
    names = [c["name"] for c in config_data.get("clusters", [])]
    if len(names) != len(set(names)):
        duplicates = [n for n in names if names.count(n) > 1]
        raise ValueError(f"Duplicate cluster names found: {set(duplicates)}")

def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration from JSON file.

    Supports both multi-cluster and legacy single-cluster formats.
    Legacy configs are automatically converted to multi-cluster format.

    Multi-cluster format:
        {
            "clusters": [
                {"name": "Building 4", "proxmox": {...}, "auth": {...}},
                {"name": "Building 3", "proxmox": {...}, "auth": {...}}
            ],
            "logging": {...}
        }

    Legacy format (auto-converted):
        {
            "proxmox": {...},
            "auth": {...},
            "logging": {...}
        }

    Args:
        config_path: Path to the JSON configuration file

    Returns:
        Config object containing validated configuration

    Raises:
        ValueError: If config path not provided, JSON invalid,
                    required fields missing, or duplicate cluster names
    """
    if not config_path:
        raise ValueError("PROXMOX_MCP_CONFIG environment variable must be set")

    try:
        with open(config_path) as f:
            config_data = json.load(f)

            # Check if this is a legacy config (has 'proxmox' at root level)
            if "proxmox" in config_data and "clusters" not in config_data:
                if not config_data.get('proxmox', {}).get('host'):
                    raise ValueError("Proxmox host cannot be empty")
                config_data = _convert_legacy_config(config_data)

            # Validate new format
            if "clusters" in config_data:
                if not config_data["clusters"]:
                    raise ValueError("At least one cluster must be configured")
                _validate_cluster_names(config_data)
                for cluster in config_data["clusters"]:
                    if not cluster.get("proxmox", {}).get("host"):
                        raise ValueError(f"Proxmox host cannot be empty for cluster '{cluster.get('name', 'unknown')}'")

            return Config(**config_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load config: {e}")
