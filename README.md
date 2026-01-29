# SciWeave

A contract for ML experiments that humans and AI agents both follow.

SciWeave provides a minimal structure for experiments: you define *what you're trying* (config), *what you do* (logic), and *what you get back* (results). Everything else—tracking, logging, artifacts—is handled automatically.

## The Problem

The typical ML research workflow:

```
experiment_v1.py
experiment_v2.py
experiment_v2_fixed.py
experiment_v2_final.py
experiment_v2_final_FINAL.py
results_jan24/
results_jan24_new/
backup_dont_delete/
```

After weeks of exploration, you have scripts with hardcoded parameters, results scattered across folders, and no clear record of what config produced what outcome.

When AI coding agents enter the picture, this gets worse. Without structure, agents produce the same ad-hoc mess—just faster.

## Philosophy: What is an Experiment?

An experiment has exactly **three components**:

| Component | What it is | Example |
|-----------|------------|---------|
| **Config** | What you're trying | `{"lr": 0.001, "layers": 4}` |
| **Logic** | What you do | Train a model, run an analysis |
| **Results** | What you get back | `{"accuracy": 0.95, "loss": 0.02}` |

Everything else—file I/O, tracking servers, parameter logging, artifact storage—is infrastructure noise that shouldn't leak into your experiment code.

The `Experiment` base class enforces this contract:

```python
class MyExperiment(Experiment):
    def run(self):
        # Config comes in via self.config
        model = build_model(self.config["model"])

        # Your logic goes here
        train(model)

        # Results go out via return
        return {"accuracy": evaluate(model)}
```

That's it. Config in, logic in the middle, results out.

## What Subclassing Actually Does

When you call `exp()`, here's what happens under the hood:

```
exp = MyExperiment(project, "experiment_name", config)
results = exp()  # This triggers the following:
```

```
┌─────────────────────────────────────────────────────────┐
│  1. mlflow.start_run()                                  │
│     └── Creates a new tracked run in MLflow             │
│                                                         │
│  2. mlflow.log_params(flatten(config))                  │
│     └── {"model.lr": "0.001", "model.layers": "4"}      │
│                                                         │
│  3. results = self.run()    ← Your code runs here       │
│     └── You have access to self.log_metric(), etc.      │
│                                                         │
│  4. mlflow.log_metrics(results)                         │
│     └── {"accuracy": 0.95, "loss": 0.02}                │
│                                                         │
│  5. mlflow.end_run()                                    │
│     └── Run is complete and tracked                     │
└─────────────────────────────────────────────────────────┘
```

You focus on the logic. SciWeave handles the tracking.

## The Bigger Picture: Agent-Driven Research

SciWeave is designed for a world where AI agents help run experiments. The MCP (Model Context Protocol) server gives agents like Claude Code the tools to manage the full experiment lifecycle:

```
┌─────────────────────────────────────────────────────────┐
│  OBSIDIAN VAULT                                         │
│  └── experiments/                                       │
│       └── sae_feature_geometry.md  (proposal)           │
└────────────────────┬────────────────────────────────────┘
                     │ vault_read_proposal()
                     ▼
┌─────────────────────────────────────────────────────────┐
│  CLAUDE CODE reads the proposal                         │
│  "Implement an experiment to analyze SAE features..."   │
└────────────────────┬────────────────────────────────────┘
                     │ scaffold_experiment()
                     ▼
┌─────────────────────────────────────────────────────────┐
│  WORKSPACE                                              │
│  └── sae_feature_geometry/                              │
│       ├── sae_feature_geometry.py  (generated scaffold) │
│       ├── spec.yaml                                     │
│       └── journal.md                                    │
└────────────────────┬────────────────────────────────────┘
                     │ Agent implements run() method
                     ▼
┌─────────────────────────────────────────────────────────┐
│  USER runs the experiment                               │
│  $ python sae_feature_geometry.py                       │
└────────────────────┬────────────────────────────────────┘
                     │ Results logged to MLflow
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MLFLOW / DATABRICKS                                    │
│  └── Params, metrics, artifacts tracked                 │
└────────────────────┬────────────────────────────────────┘
                     │ get_latest_run(), compare_runs()
                     ▼
┌─────────────────────────────────────────────────────────┐
│  CLAUDE CODE analyzes results                           │
│  "The accuracy improved by 12% when..."                 │
└────────────────────┬────────────────────────────────────┘
                     │ journal_append()
                     ▼
┌─────────────────────────────────────────────────────────┐
│  JOURNAL updated with analysis                          │
│  └── journal.md now contains run results & insights     │
└─────────────────────────────────────────────────────────┘
```

The MCP server is the interface layer that gives agents eyes (query tools) and hands (scaffold/journal tools) to work with your experiments.

> **Note**: Experiment proposals can come from anywhere—manually written, generated by [Scigest](https://github.com/vivekhandebagh/scigest), or any other source. SciWeave just needs a vault path to read from.

## Quick Start

### 1. Install

```bash
pip install sciweave
# or
uv pip install sciweave
```

### 2. Create a Project

```python
from sciweave import Project, Experiment

# Connect to Databricks
project = Project("my-research", tracking_uri="databricks")

# Or local MLflow
project = Project("my-research", tracking_uri="http://localhost:5000")

# Or file-based (for testing)
project = Project("my-research", tracking_uri="./mlruns")
```

### 3. Define and Run an Experiment

```python
class TrainingExperiment(Experiment):
    def run(self):
        model = build_model(self.config["model"])

        for epoch in range(self.config["epochs"]):
            loss = train_epoch(model)
            self.log_metric("loss", loss, step=epoch)  # Time-series

        self.log_artifact("model.pt")  # Save model

        return {"final_loss": loss}

# Run it
exp = TrainingExperiment(
    project,
    "transformer_v1",
    config={"model": {"hidden": 256}, "epochs": 100}
)
results = exp()
```

## API Reference

### Project

```python
Project(name: str, tracking_uri: str = "databricks")
```

| Parameter | Description |
|-----------|-------------|
| `name` | Project name (MLflow experiment prefix) |
| `tracking_uri` | `"databricks"`, `"http://host:port"`, or `"./path"` |

### Experiment

```python
Experiment(project, experiment_name, config, run_name=None, tags=None)
```

**Methods available inside `run()`:**

| Method | Description |
|--------|-------------|
| `self.config` | Your config dict (original nested structure) |
| `self.log_metric(key, value, step=None)` | Log a metric (use `step` for time-series) |
| `self.log_metrics(dict, step=None)` | Log multiple metrics |
| `self.log_artifact(path)` | Log a file |
| `self.log_figure(figure, filename)` | Log a matplotlib figure |
| `self.set_tag(key, value)` | Set a tag |

**Config flattening**: `{"model": {"lr": 0.001}}` → logged as `model.lr=0.001`

## MCP Server

The MCP server provides 17 tools for AI agents:

| Category | Tools | Purpose |
|----------|-------|---------|
| **MLflow Query** (8) | `list_experiments`, `search_runs`, `get_run`, `get_latest_run`, `get_best_run`, `get_metric_history`, `compare_runs`, `list_artifacts` | Read experiment data |
| **Vault** (3) | `vault_list_proposals`, `vault_read_proposal`, `vault_update_status` | Access proposals |
| **Scaffold** (2) | `scaffold_experiment`, `validate_experiment` | Generate code |
| **Journal** (4) | `journal_new_run`, `journal_append`, `journal_update_status`, `journal_read` | Track progress |

### Setup

```bash
cd sciweave-mcp
uv sync
```

Add to your Claude Code config (`.mcp.json`):

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
        "SCIWEAVE_VAULT_PATH": "/path/to/vault/experiments",
        "SCIWEAVE_WORKSPACE_PATH": "/path/to/workspace"
      }
    }
  }
}
```

See [sciweave-mcp/README.md](sciweave-mcp/README.md) for full MCP documentation.

## Environment Setup

### Databricks

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token"
```

### Local MLflow

```bash
mlflow server --port 5000
# Then use tracking_uri="http://localhost:5000"
```

## Status

v0.2.0 - MLflow-first design. API is stabilizing but may still change.

## License

MIT
