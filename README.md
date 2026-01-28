# SciWeave

Structured experiment scaffolding for ML research teams. SciWeave provides a clean, opinionated structure for experiments that logs directly to MLflow/Databricks.

## The Problem

The typical researcher workflow involves writing ad-hoc Python scripts, running them with different parameters manually edited in the code, and saving results to variously named CSV files or folders. After weeks of exploration, researchers find themselves with directories full of `experiment_v2_final_FINAL.py` scripts and results scattered across `results_020124/`, `test_runs_new/`, and `backup_dont_delete/`.

When AI coding agents enter the picture, this gets worse. Without structure, agents produce the same ad-hoc mess—just faster.

## The Solution

SciWeave provides a simple scaffold: subclass `Experiment`, implement `run()`, return your results. Everything else—logging configs, tracking metrics, saving artifacts—is handled automatically to your team's MLflow/Databricks instance.

```python
from sciweave import Project, Experiment

project = Project("my-research", tracking_uri="databricks")

class MyExperiment(Experiment):
    def run(self):
        model = train_model(self.config)
        return {"accuracy": 0.95, "loss": 0.05}

exp = MyExperiment(project, "transformer_v1", {"lr": 0.001, "epochs": 100})
results = exp()  # Logged to MLflow automatically
```

## Key Features

- **Simple Structure**: Subclass `Experiment`, implement `run()`, done
- **MLflow Integration**: Configs logged as params, results as metrics
- **Time-Series Metrics**: `self.log_metric("loss", value, step=epoch)` for training curves
- **Artifact Storage**: `self.log_artifact("model.pt")` for models, plots, data
- **Nested Configs**: `{"model": {"hidden": 256}}` flattened to `model.hidden` params
- **Team Collaboration**: Everyone logs to the same Databricks/MLflow instance
- **Agent-Friendly**: Gives AI coding agents a clear contract to follow

## Installation

```bash
pip install sciweave

# Or with uv
uv pip install sciweave

# Or from source
git clone https://github.com/vivekhandebagh/sciweave.git
cd sciweave
uv pip install -e .
```

## Quick Start

### 1. Create a Project

```python
from sciweave import Project, Experiment

# Connect to Databricks MLflow
project = Project("my-research", tracking_uri="databricks")

# Or local MLflow server
project = Project("my-research", tracking_uri="http://localhost:5000")

# Or local file storage (for testing)
project = Project("my-research", tracking_uri="./mlruns")
```

### 2. Define an Experiment

```python
class TrainingExperiment(Experiment):
    def run(self):
        config = self.config  # Your nested config dict

        model = build_model(config["model"])
        optimizer = create_optimizer(model, config["training"])

        for epoch in range(config["epochs"]):
            loss = train_epoch(model, optimizer)
            val_acc = evaluate(model)

            # Log metrics with step for time-series
            self.log_metric("train_loss", loss, step=epoch)
            self.log_metric("val_accuracy", val_acc, step=epoch)

        # Save model artifact
        torch.save(model.state_dict(), "model.pt")
        self.log_artifact("model.pt")

        # Return final results (logged as metrics)
        return {
            "final_loss": loss,
            "final_accuracy": val_acc,
            "best_epoch": best_epoch
        }
```

### 3. Run It

```python
config = {
    "model": {
        "hidden_size": 256,
        "num_layers": 4,
        "dropout": 0.1
    },
    "training": {
        "lr": 0.001,
        "batch_size": 32
    },
    "epochs": 100
}

exp = TrainingExperiment(
    project,
    "transformer_experiment",
    config,
    run_name="baseline-v1",
    tags={"team": "research", "version": "v1"}
)

results = exp()
print(f"Final accuracy: {results['final_accuracy']}")
```

## API Reference

### Project

```python
Project(name: str, tracking_uri: str = "databricks")
```

- `name`: Project name (used as MLflow experiment prefix)
- `tracking_uri`: MLflow tracking URI
  - `"databricks"`: Use Databricks (requires `DATABRICKS_HOST` and `DATABRICKS_TOKEN` env vars)
  - `"http://host:port"`: Remote MLflow server
  - `"./path"`: Local file storage

### Experiment

```python
Experiment(
    project: Project,
    experiment_name: str,
    config: dict,
    run_name: str = None,
    tags: dict = None
)
```

**Methods available in `run()`:**

| Method | Description |
|--------|-------------|
| `self.config` | Access your config dict (original nested structure) |
| `self.log_metric(key, value, step=None)` | Log a metric (use `step` for time-series) |
| `self.log_metrics(dict, step=None)` | Log multiple metrics at once |
| `self.log_artifact(path, artifact_path=None)` | Log a file (model, plot, data) |
| `self.log_artifacts(dir, artifact_path=None)` | Log all files in a directory |
| `self.log_figure(figure, filename)` | Log a matplotlib figure |
| `self.log_dict(dict, filename)` | Log a dict as JSON/YAML |
| `self.set_tag(key, value)` | Set a custom tag |
| `self.run_id` | Get the current MLflow run ID |

### Config Flattening

Nested configs are automatically flattened for MLflow params:

```python
# Your config
{
    "model": {"hidden": 256, "layers": 4},
    "lr": 0.001
}

# Logged as MLflow params
{
    "model.hidden": "256",
    "model.layers": "4",
    "lr": "0.001"
}
```

## Databricks Setup

1. Set environment variables:
   ```bash
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   export DATABRICKS_TOKEN="your-personal-access-token"
   ```

2. Use `tracking_uri="databricks"`:
   ```python
   project = Project("my-research", tracking_uri="databricks")
   ```

3. Experiments appear in your Databricks workspace under MLflow Experiments.

## Local Development

For local testing without Databricks:

```bash
# Start local MLflow server
mlflow server --port 5000

# In your code
project = Project("my-research", tracking_uri="http://localhost:5000")
```

Or use file-based tracking:
```python
project = Project("my-research", tracking_uri="./mlruns")
```

## Querying Results

Use MLflow's UI or API to query results:

```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("databricks")

# Search runs
runs = mlflow.search_runs(
    experiment_names=["my-research/transformer_experiment"],
    filter_string="metrics.final_accuracy > 0.9"
)

print(runs[["params.model.hidden", "metrics.final_accuracy"]])
```

Or use the MLflow UI at your Databricks workspace or `http://localhost:5000`.

## For AI Coding Agents

SciWeave gives AI agents a clear contract:

1. Subclass `Experiment`
2. Implement `run()` method
3. Access config via `self.config`
4. Log metrics with `self.log_metric()`
5. Return results as a dict

This structure prevents agents from creating ad-hoc scripts and ensures all experiments are tracked consistently.

## Example: Full Training Pipeline

```python
from sciweave import Project, Experiment
import torch
import torch.nn as nn

project = Project("nlp-research", tracking_uri="databricks")

class LanguageModelExperiment(Experiment):
    def run(self):
        # Access nested config naturally
        model_cfg = self.config["model"]
        train_cfg = self.config["training"]

        # Build model
        model = TransformerLM(
            vocab_size=model_cfg["vocab_size"],
            d_model=model_cfg["d_model"],
            n_heads=model_cfg["n_heads"],
            n_layers=model_cfg["n_layers"]
        )

        optimizer = torch.optim.AdamW(model.parameters(), lr=train_cfg["lr"])

        best_loss = float("inf")

        for epoch in range(train_cfg["epochs"]):
            # Training
            train_loss = train_epoch(model, optimizer, train_loader)
            val_loss = evaluate(model, val_loader)

            # Log time-series metrics
            self.log_metrics({
                "train_loss": train_loss,
                "val_loss": val_loss,
                "learning_rate": optimizer.param_groups[0]["lr"]
            }, step=epoch)

            # Save best model
            if val_loss < best_loss:
                best_loss = val_loss
                torch.save(model.state_dict(), "best_model.pt")
                self.log_artifact("best_model.pt", "models")

        # Log final model
        torch.save(model.state_dict(), "final_model.pt")
        self.log_artifact("final_model.pt", "models")

        # Return final metrics
        return {
            "final_train_loss": train_loss,
            "final_val_loss": val_loss,
            "best_val_loss": best_loss,
        }

# Run experiment
config = {
    "model": {
        "vocab_size": 50000,
        "d_model": 512,
        "n_heads": 8,
        "n_layers": 6
    },
    "training": {
        "lr": 1e-4,
        "epochs": 50,
        "batch_size": 32
    }
}

exp = LanguageModelExperiment(
    project,
    "transformer_lm",
    config,
    run_name="baseline",
    tags={"model_type": "transformer", "dataset": "wikitext"}
)

results = exp()
```

## MCP Server for AI Agents

SciWeave includes an MCP (Model Context Protocol) server that gives AI coding agents like Claude Code access to experiment management tools.

### Quick Setup

```bash
cd sciweave-mcp
uv sync
```

Add to `.mcp.json`:

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
        "SCIWEAVE_VAULT_PATH": "/path/to/obsidian/vault",
        "SCIWEAVE_WORKSPACE_PATH": "/path/to/workspace"
      }
    }
  }
}
```

### Available Tools (17 total)

**MLflow Query (8 tools)**
- `list_experiments` - List all experiments
- `search_runs` - Search with filters
- `get_run` - Get run details
- `get_latest_run` - Get most recent run
- `get_best_run` - Find best by metric
- `get_metric_history` - Get training curves
- `compare_runs` - Compare side-by-side
- `list_artifacts` - List run artifacts

**Vault (3 tools)** - Read experiment proposals from Obsidian
- `vault_list_proposals` - List proposals
- `vault_read_proposal` - Read full content
- `vault_update_status` - Update status

**Scaffold (2 tools)** - Generate experiment code
- `scaffold_experiment` - Create boilerplate
- `validate_experiment` - Check patterns

**Journal (4 tools)** - Track runs
- `journal_new_run` - Start new entry
- `journal_append` - Add to section
- `journal_update_status` - Update status
- `journal_read` - Read journal

See [sciweave-mcp/README.md](sciweave-mcp/README.md) for full documentation.

## Contributing

Contributions welcome! This is an early release and we're actively looking for feedback.

## License

MIT License

## Status

v0.2.0 - MLflow-first redesign with unified MCP server. The API is stabilizing but may still change.

## Support

- Issues: [GitHub Issues](https://github.com/vivekhandebagh/sciweave/issues)
- Discussions: [GitHub Discussions](https://github.com/vivekhandebagh/sciweave/discussions)
