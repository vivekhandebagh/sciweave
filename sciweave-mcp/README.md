# SciWeave MCP Server

Unified MCP server for experiment management with AI coding agents. Provides 17 tools across 4 categories: MLflow queries, vault access, experiment scaffolding, and run journaling.

## Installation

```bash
cd sciweave-mcp
uv sync
```

## Configuration

Add to your Claude Code MCP settings (`.mcp.json` or `.claude/settings.json`):

### Full Configuration (All Tools)

```json
{
  "mcpServers": {
    "sciweave-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/sciweave-mcp", "run", "sciweave-mcp"],
      "env": {
        "MLFLOW_TRACKING_URI": "databricks",
        "DATABRICKS_HOST": "https://your-workspace.cloud.databricks.com",
        "DATABRICKS_TOKEN": "your-token",
        "SCIWEAVE_VAULT_PATH": "/path/to/obsidian/vault/experiments",
        "SCIWEAVE_WORKSPACE_PATH": "/path/to/workspace"
      }
    }
  }
}
```

### MLflow-Only Configuration

If you only need MLflow query tools:

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

### Local MLflow

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MLFLOW_TRACKING_URI` | Yes | MLflow tracking URI (`databricks`, `http://host:port`, or file path) |
| `DATABRICKS_HOST` | For Databricks | Databricks workspace URL |
| `DATABRICKS_TOKEN` | For Databricks | Databricks personal access token |
| `SCIWEAVE_VAULT_PATH` | For vault/scaffold tools | Path to Obsidian vault with experiment proposals |
| `SCIWEAVE_WORKSPACE_PATH` | For scaffold/journal tools | Path to workspace for generated experiments |

## Available Tools

### MLflow Query Tools (8)

Query experiment data from MLflow/Databricks.

| Tool | Description |
|------|-------------|
| `list_experiments` | List all MLflow experiments, optionally filtered by prefix |
| `search_runs` | Search runs with filters (e.g., `metrics.accuracy > 0.9`) |
| `get_run` | Get complete details of a specific run (all params, metrics, tags) |
| `get_latest_run` | Get the most recent run's full details from an experiment |
| `get_best_run` | Find the best run by a metric (max or min) |
| `get_metric_history` | Get metric values across training steps |
| `compare_runs` | Compare multiple runs side-by-side |
| `list_artifacts` | List artifacts for a run |

### Vault Tools (3)

Access experiment proposals from Obsidian vault (created by Scigest or manually).

| Tool | Description |
|------|-------------|
| `vault_list_proposals` | List proposals, optionally filtered by status |
| `vault_read_proposal` | Read full proposal content including sections |
| `vault_update_status` | Update proposal status (proposed → spec_ready → completed) |

### Scaffold Tools (2)

Generate experiment boilerplate code.

| Tool | Description |
|------|-------------|
| `scaffold_experiment` | Create experiment directory with Python file, spec.yaml, and journal.md |
| `validate_experiment` | Check that experiment code follows sciweave patterns |

### Journal Tools (4)

Track experiment runs and enable human-AI collaboration.

| Tool | Description |
|------|-------------|
| `journal_new_run` | Start a new run section in the experiment journal |
| `journal_append` | Append content to a specific section (results, analysis, issues, etc.) |
| `journal_update_status` | Update run status (PENDING → RUNNING → SUCCESS/FAILED) |
| `journal_read` | Read the full journal for an experiment |

## Usage Examples

### Querying Results

After running a SciWeave experiment, ask Claude:

- "What were the results of my last experiment?"
- "Show me the loss curve for run abc123"
- "Find runs with accuracy > 0.9"
- "Compare my last 3 runs"

### Reading Proposals

When starting a new experiment:

- "List all proposed experiments"
- "Read the SAE feature geometry proposal"
- "What experiments are ready for implementation?"

### Scaffolding Experiments

When implementing a proposal:

- "Create an experiment scaffold for the SAE analysis"
- "Validate my experiment code"

### Journaling Runs

During and after experiment runs:

- "Start a new run in the journal"
- "Update the journal with these results: accuracy=0.95, loss=0.05"
- "Mark the run as successful"

## Workflow

The typical workflow with Claude Code:

1. **Read proposal**: `vault_read_proposal("sae_geometry")`
2. **Scaffold experiment**: `scaffold_experiment("sae_geometry", {...spec...})`
3. **Implement run()**: Claude fills in the experiment logic
4. **Start journal entry**: `journal_new_run("sae_geometry")`
5. **Run experiment**: User executes the Python file
6. **Check results**: `get_latest_run("my-project/sae_geometry")`
7. **Update journal**: `journal_append("sae_geometry", "results", "...")`
8. **Update status**: `vault_update_status("sae_geometry", "completed")`

## Scaffold Output

When you call `scaffold_experiment`, it creates:

```
workspace/
└── experiment_name/
    ├── experiment_name.py    # Python file with Experiment subclass
    ├── spec.yaml             # Original specification
    ├── journal.md            # Run journal for tracking
    ├── results/              # Directory for outputs
    ├── configs/              # Directory for config files
    └── data/                 # Directory for data files
```

The generated Python file follows the sciweave pattern:

```python
from sciweave import Project, Experiment

class MyExperiment(Experiment):
    def run(self):
        # TODO: Implement experiment logic
        return {"metric": value}

if __name__ == "__main__":
    project = Project("experiments", tracking_uri="databricks")
    exp = MyExperiment(project, "experiment_name", config)
    results = exp()
```

## Journal Format

The journal tracks runs in a structured format:

```markdown
# Experiment Journal: My Experiment

## Spec Summary
- **Hypothesis:** ...
- **Success Criteria:** ...

---

## Run 1 - 2024-01-15 14:30

### Execution
- Status: SUCCESS
- Duration: 45 minutes
- Config: lr=0.001, epochs=100

### Results
| Metric | Value |
|--------|-------|
| accuracy | 0.95 |
| loss | 0.05 |

### Analysis
The model converged well...

### Issues
None

### Next Steps
Try larger batch size

### Human Notes
Approved for production testing
```

## Testing

```bash
# Verify tools are registered
uv run python -c "from sciweave_mcp.server import mcp; print(list(mcp._tool_manager._tools.keys()))"

# Test with MCP Inspector
mcp dev sciweave_mcp/server.py
```

## Fallback Configuration

If environment variables are not set, the server falls back to `~/.sciweave/config.yaml`:

```yaml
mlflow:
  tracking_uri: databricks

vault:
  experiments_path: /path/to/obsidian/vault/experiments

workspace:
  path: /path/to/workspace
```

## Dependencies

- `mcp[cli]>=1.2.0` - MCP server framework
- `mlflow>=2.0.0` - MLflow client
- `pydantic>=2.0` - Data validation
- `pyyaml>=6.0` - YAML parsing
