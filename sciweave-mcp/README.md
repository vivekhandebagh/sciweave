# SciWeave MCP Server

MCP server for querying MLflow experiments from AI coding agents.

## Installation

```bash
cd sciweave-mcp
uv sync
```

## Configuration

Add to your Claude Code settings (`.claude/settings.json`):

**For Databricks:**
```json
{
  "mcpServers": {
    "sciweave-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/sciweave-mcp", "run", "sciweave-mcp"],
      "env": {
        "MLFLOW_TRACKING_URI": "databricks",
        "DATABRICKS_HOST": "https://your-workspace.cloud.databricks.com",
        "DATABRICKS_TOKEN": "your-token"
      }
    }
  }
}
```

**For Local MLflow:**
```json
{
  "mcpServers": {
    "sciweave-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/sciweave-mcp", "run", "sciweave-mcp"],
      "env": {
        "MLFLOW_TRACKING_URI": "http://localhost:5000"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_experiments` | List all MLflow experiments |
| `search_runs` | Search/filter runs in an experiment |
| `get_run` | Get complete details of a specific run |
| `get_latest_run` | Get the most recent run's full details |
| `get_metric_history` | Get metric values over training steps |
| `get_best_run` | Find the best run by a metric |
| `compare_runs` | Compare multiple runs side-by-side |
| `list_artifacts` | List artifacts for a run |

## Usage Examples

After running a SciWeave experiment, ask Claude:

- "What were the results of my last experiment?"
- "Show me the loss curve for run abc123"
- "Find runs with accuracy > 0.9"
- "Compare runs abc123, def456, ghi789"

## Testing

```bash
# Test with MCP Inspector
mcp dev sciweave_mcp/server.py
```
