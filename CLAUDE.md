# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SciWeave is a structured experiment scaffolding framework for ML research teams. It provides a clean `Experiment` base class that logs directly to MLflow/Databricks.

## Development Commands

```bash
# Install for development
uv pip install -e .

# Sync dependencies
uv sync

# Run tests
python -m pytest sciweave/tests/test_mlflow.py -v
```

## Architecture

### Core Components

**Project** (`sciweave/project.py`) - Thin MLflow wrapper:
- Connects to MLflow tracking server (Databricks, remote, or local)
- Creates/retrieves MLflow experiments with project name prefix
- ~50 lines of code

**Experiment** (`sciweave/experiment.py`) - Abstract base class users extend:
- Users subclass and implement `run()` method returning a results dict
- `__call__` handles: start MLflow run, log params, execute run(), log results, end run
- Provides logging methods: `log_metric()`, `log_artifact()`, `log_figure()`, etc.
- ~150 lines of code

**Config** (`sciweave/config.py`) - Config flattening utility:
- `flatten_config()` converts nested dicts to flat string params for MLflow
- Handles OmegaConf DictConfig objects
- ~40 lines of code

### Data Flow

```
User Code
    │
    ▼
Experiment.__call__()
    ├── mlflow.start_run()
    ├── mlflow.log_params(flatten_config(config))
    ├── user's run() method
    │   ├── self.log_metric(key, value, step)  → mlflow.log_metric()
    │   ├── self.log_artifact(path)            → mlflow.log_artifact()
    │   └── return {"accuracy": 0.95}
    ├── mlflow.log_metric() for each result
    └── mlflow.end_run()
    │
    ▼
MLflow Tracking Server (Databricks/local)
```

### File Structure

```
sciweave/
├── __init__.py      # Exports: Project, Experiment, flatten_config
├── project.py       # Project class
├── experiment.py    # Experiment ABC
├── config.py        # flatten_config()
└── tests/
    └── test_mlflow.py
```

## Key Patterns

- **MLflow-first**: All tracking goes to MLflow, no local database
- **Config Flattening**: `{"model": {"lr": 0.01}}` → `{"model.lr": "0.01"}` for MLflow params
- **Structured Results**: Return dict from `run()` → logged as MLflow metrics/tags
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

## Dependencies

- `mlflow>=2.0.0` (core dependency)
- `pytest>=7.0.0` (dev dependency)
