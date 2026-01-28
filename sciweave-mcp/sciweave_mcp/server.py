"""SciWeave MCP Server - Unified experiment management for AI agents.

Provides 18 tools across four categories:
- MLflow Query (8 tools): Access experiment runs, metrics, and artifacts
- Vault (3 tools): Read experiment proposals from Obsidian vault
- Scaffold (2 tools): Create experiment boilerplate code
- Journal (5 tools): Track experiment runs and collaboration
"""

import logging

from mcp.server.fastmcp import FastMCP

from sciweave_mcp.tools.mlflow import register_mlflow_tools
from sciweave_mcp.tools.vault import register_vault_tools
from sciweave_mcp.tools.scaffold import register_scaffold_tools
from sciweave_mcp.tools.journal import register_journal_tools

# Configure logging to stderr (required for stdio transport)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("sciweave-mcp")

# Register all tool groups
register_mlflow_tools(mcp)
register_vault_tools(mcp)
register_scaffold_tools(mcp)
register_journal_tools(mcp)


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
