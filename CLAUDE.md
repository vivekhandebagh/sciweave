# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SciWeave is a structured experiment framework for ML research teams:
- **sciweave/** - Python library with `Project` and `Experiment` base classes for MLflow tracking
- **sciweave-mcp/** - Unified MCP server providing 18 tools for experiment management

## Development Commands

### Library
```bash
cd sciweave
uv pip install -e .
uv sync
python -m pytest sciweave/tests/test_mlflow.py -v
```

### MCP Server
```bash
cd sciweave-mcp
uv sync
uv run sciweave-mcp  # Start server
```

## Architecture

### Library Components (`sciweave/`)

**Project** (`project.py`) - Thin MLflow wrapper:
- Connects to MLflow tracking server (Databricks, remote, or local)
- Creates/retrieves MLflow experiments with project name prefix
- ~50 lines of code

**Experiment** (`experiment.py`) - Abstract base class users extend:
- Users subclass and implement `run()` method returning a results dict
- `__call__` handles: start MLflow run, log params, execute run(), log results, end run
- Provides logging methods: `log_metric()`, `log_artifact()`, `log_figure()`, etc.
- ~150 lines of code

**Config** (`config.py`) - Config flattening utility:
- `flatten_config()` converts nested dicts to flat string params for MLflow

### MCP Server (`sciweave-mcp/`)

Single entry point providing 18 tools across 4 categories:

**MLflow Query (8 tools)** - Read experiment data:
| Tool | Purpose |
|------|---------|
| `list_experiments` | List all MLflow experiments |
| `search_runs` | Search runs with filters |
| `get_run` | Get complete run details |
| `get_latest_run` | Get most recent run |
| `get_best_run` | Find best run by metric |
| `get_metric_history` | Get metric across steps |
| `compare_runs` | Compare runs side by side |
| `list_artifacts` | List run artifacts |

**Vault (3 tools)** - Read Hedorah proposals:
| Tool | Purpose |
|------|---------|
| `vault_list_proposals` | List proposals from Obsidian |
| `vault_read_proposal` | Read full proposal content |
| `vault_update_status` | Update proposal status |

**Scaffold (2 tools)** - Generate code:
| Tool | Purpose |
|------|---------|
| `scaffold_experiment` | Create experiment boilerplate |
| `validate_experiment` | Check code follows patterns |

**Journal (5 tools)** - Track runs:
| Tool | Purpose |
|------|---------|
| `journal_new_run` | Start new journal entry |
| `journal_append` | Append to section |
| `journal_update_status` | Update run status |
| `journal_read` | Read full journal |

### Data Flow

```
Hedorah (paper processor)
    │
    ▼
Obsidian Vault (proposals)
    │
    ├─→ vault_read_proposal()
    │
    ▼
scaffold_experiment()
    │
    ▼
User implements run() method
    │
    ▼
Experiment.__call__()
    ├── mlflow.start_run()
    ├── mlflow.log_params(config)
    ├── user's run() method
    ├── mlflow.log_metrics(results)
    └── mlflow.end_run()
    │
    ▼
MLflow Tracking Server
    │
    ├─→ get_latest_run()
    ├─→ get_metric_history()
    └─→ compare_runs()
```

## Configuration

### Environment Variables
```bash
# MLflow (required)
MLFLOW_TRACKING_URI=databricks
DATABRICKS_HOST=https://...
DATABRICKS_TOKEN=dapi...

# Scaffolding (required for vault/scaffold/journal tools)
SCIWEAVE_VAULT_PATH=/path/to/obsidian/vault/experiments
SCIWEAVE_WORKSPACE_PATH=/path/to/workspace
```

### MCP Configuration (`.mcp.json`)
```json
{
  "mcpServers": {
    "sciweave-mcp": {
      "command": "uv",
      "args": ["--directory", "sciweave-mcp", "run", "sciweave-mcp"],
      "env": {
        "MLFLOW_TRACKING_URI": "databricks",
        "SCIWEAVE_VAULT_PATH": "/path/to/vault",
        "SCIWEAVE_WORKSPACE_PATH": "/path/to/workspace"
      }
    }
  }
}
```

## Key Patterns

- **MLflow-first**: All tracking goes to MLflow, no local database
- **Config Flattening**: `{"model": {"lr": 0.01}}` → `{"model.lr": "0.01"}` for MLflow params
- **Structured Results**: Return dict from `run()` → logged as MLflow metrics
- **Time-series Metrics**: `self.log_metric(key, value, step=epoch)` for training curves

## Usage Pattern

```python
from sciweave import Project, Experiment

project = Project("my-research", tracking_uri="databricks")

class MyExperiment(Experiment):
    def run(self):
        for epoch in range(self.config["epochs"]):
            loss = train_epoch()
            self.log_metric("loss", loss, step=epoch)
        return {"final_loss": loss}

exp = MyExperiment(project, "experiment_name", {"lr": 0.01, "epochs": 10})
results = exp()
```

## Python Version

Requires Python 3.11+
