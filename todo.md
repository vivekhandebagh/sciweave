# SciWeave Status & Roadmap

## Current State (v0.2.0)

### Completed

- [x] **MLflow-first architecture** - All tracking goes to MLflow, no local SQLite database
- [x] **Project class** - Thin wrapper for MLflow experiment management
- [x] **Experiment base class** - Clean `run()` pattern with automatic logging
- [x] **Config flattening** - Nested dicts flattened for MLflow params
- [x] **Time-series metrics** - `self.log_metric(key, value, step=epoch)` for training curves
- [x] **Artifact logging** - `self.log_artifact()`, `self.log_figure()`, etc.
- [x] **Unified MCP server** - 17 tools in a single server
- [x] **MLflow query tools** (8) - list_experiments, search_runs, get_run, get_latest_run, get_best_run, get_metric_history, compare_runs, list_artifacts
- [x] **Vault tools** (3) - Access Scigest proposals from Obsidian
- [x] **Scaffold tools** (2) - Generate experiment boilerplate
- [x] **Journal tools** (4) - Track runs with structured markdown

### Architecture

```
sciweave/
├── sciweave/                    # Python library
│   ├── project.py               # Project class
│   ├── experiment.py            # Experiment base class
│   └── config.py                # flatten_config()
└── sciweave-mcp/                # Unified MCP server (17 tools)
    └── sciweave_mcp/
        ├── server.py
        ├── config.py
        ├── tools/
        │   ├── mlflow.py        # 8 query tools
        │   ├── vault.py         # 3 vault tools
        │   ├── scaffold.py      # 2 scaffold tools
        │   └── journal.py       # 4 journal tools
        ├── models/
        │   └── spec.py          # ExperimentSpec Pydantic model
        └── templates/
            └── experiment.py.template
```

## Roadmap

### Short Term

- [ ] **Documentation** - Full API reference and tutorials
- [ ] **Testing** - Expand test coverage for MCP tools
- [ ] **Templates** - Additional experiment templates for common patterns
- [ ] **Validation** - More robust experiment validation

### Medium Term

- [ ] **Model logging** - Auto-detect framework (PyTorch, sklearn, etc.)
- [ ] **Artifact retrieval** - MCP tool to read artifact contents
- [ ] **Batch operations** - Run multiple experiments with parameter sweeps
- [ ] **Visualization** - Generate plots from experiment history

### Long Term

- [ ] **Unity Catalog** - Databricks Unity Catalog integration
- [ ] **Team features** - Notifications, permissions, workflows
- [ ] **CI/CD integration** - GitHub Actions for experiment runs
- [ ] **Web dashboard** - Optional visualization UI

## Known Issues

- Vault/scaffold/journal tools require `SCIWEAVE_VAULT_PATH` and `SCIWEAVE_WORKSPACE_PATH` environment variables
- No artifact content retrieval via MCP (only listing)

## Configuration

### Environment Variables

```bash
# MLflow (required)
MLFLOW_TRACKING_URI=databricks
DATABRICKS_HOST=https://...
DATABRICKS_TOKEN=dapi...

# Scaffolding (for vault/scaffold/journal tools)
SCIWEAVE_VAULT_PATH=/path/to/obsidian/vault/experiments
SCIWEAVE_WORKSPACE_PATH=/path/to/workspace
```

### Fallback Config

`~/.sciweave/config.yaml`:
```yaml
mlflow:
  tracking_uri: databricks
vault:
  experiments_path: /path/to/vault
workspace:
  path: /path/to/workspace
```
