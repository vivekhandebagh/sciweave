"""Configuration for SciWeave MCP server.

Supports configuration via environment variables:
- MLFLOW_TRACKING_URI: MLflow tracking server URI (default: "databricks")
- SCIWEAVE_VAULT_PATH: Path to Obsidian vault with experiment proposals
- SCIWEAVE_WORKSPACE_PATH: Path to workspace for generated experiments

Falls back to ~/.sciweave/config.yaml if environment variables are not set.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class SciweaveConfig(BaseModel):
    """Main configuration for SciWeave MCP server."""
    mlflow_tracking_uri: str = "databricks"
    vault_experiments_path: Optional[str] = None
    workspace_path: Optional[str] = None

    @property
    def vault_path(self) -> Path:
        """Get the vault path, raising if not configured."""
        if not self.vault_experiments_path:
            raise ValueError(
                "Vault path not configured. Set SCIWEAVE_VAULT_PATH environment variable "
                "or configure vault.experiments_path in ~/.sciweave/config.yaml"
            )
        return Path(os.path.expanduser(self.vault_experiments_path))

    @property
    def workspace(self) -> Path:
        """Get the workspace path, raising if not configured."""
        if not self.workspace_path:
            raise ValueError(
                "Workspace path not configured. Set SCIWEAVE_WORKSPACE_PATH environment variable "
                "or configure workspace.path in ~/.sciweave/config.yaml"
            )
        return Path(os.path.expanduser(self.workspace_path))


_config: Optional[SciweaveConfig] = None


def _load_yaml_config() -> dict:
    """Load config from ~/.sciweave/config.yaml if it exists."""
    config_path = Path.home() / ".sciweave" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def load_config() -> SciweaveConfig:
    """Load configuration from environment variables, falling back to config file.

    Priority:
    1. Environment variables (SCIWEAVE_VAULT_PATH, SCIWEAVE_WORKSPACE_PATH, MLFLOW_TRACKING_URI)
    2. ~/.sciweave/config.yaml
    3. Defaults
    """
    global _config
    if _config is not None:
        return _config

    # Load YAML config as fallback
    yaml_config = _load_yaml_config()

    # Get values with environment variable priority
    mlflow_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        yaml_config.get("mlflow", {}).get("tracking_uri", "databricks")
    )

    vault_path = os.environ.get(
        "SCIWEAVE_VAULT_PATH",
        yaml_config.get("vault", {}).get("experiments_path")
    )

    workspace_path = os.environ.get(
        "SCIWEAVE_WORKSPACE_PATH",
        yaml_config.get("workspace", {}).get("path")
    )

    _config = SciweaveConfig(
        mlflow_tracking_uri=mlflow_uri,
        vault_experiments_path=vault_path,
        workspace_path=workspace_path,
    )

    return _config


def get_config() -> SciweaveConfig:
    """Get the loaded config (loads if not already loaded)."""
    return load_config()


def reset_config() -> None:
    """Reset the cached config (useful for testing)."""
    global _config
    _config = None
