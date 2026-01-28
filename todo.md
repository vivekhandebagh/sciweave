the goal is to figure out how to integrate sciweave scaffold with mlflow/databricks backend

# SciWeave + MLflow Integration Plan

## Executive Summary

SciWeave provides a clean experiment scaffold (the `Experiment` base class) that makes it easy to define, run, and track computational experiments. MLflow provides robust experiment tracking infrastructure with UI, artifact storage, and model registry. The MLflow MCP server enables AI agents (Claude Code, Cursor, etc.) to query experiment history via natural language.

**The integration thesis**: SciWeave becomes the *write-side abstraction* for structuring and running experiments, while MLflow + MCP handles *persistence and agent-accessible querying*. This combination gives researchers:

1. A clean, agent-friendly experiment scaffold (SciWeave)
2. Industry-standard tracking infrastructure (MLflow)
3. Natural language access to experiment history for AI assistants (MCP)

---

## Current State

### SciWeave Today

```python
class MyExperiment(Experiment):
    def run(self):
        # experiment logic
        return {"accuracy": 0.94, "loss": 0.23}

pm = ProjectManager("my_project")  # creates SQLite DB
exp = MyExperiment(pm, "experiment_name", config)
results = exp()  # tracked in local SQLite
```

**Strengths:**
- Simple, opinionated structure for experiments
- Zero infrastructure (local SQLite)
- Automatic schema evolution
- Hydra/OmegaConf compatible
- Agent-friendly contract: "implement `run()`, return a dict"

**Limitations:**
- No artifact storage (models, plots, checkpoints)
- No time-series metrics (loss curves)
- No UI for visualization
- No collaboration features
- Query API is local-only

### MLflow Today

**Strengths:**
- Mature tracking infrastructure
- Artifact storage (S3, GCS, ADLS, local)
- Model registry with lifecycle stages
- Web UI for visualization and comparison
- Autologging for common frameworks
- REST API for programmatic access

**Limitations:**
- No prescribed experiment structure (just a logging API)
- Requires server setup for full features
- Steeper learning curve

### MLflow MCP Server

Community-built MCP servers (e.g., `mlflow-mcp` by kkruglik) expose MLflow's read API to AI agents:

```
Available tools:
- get_experiments()
- get_runs(experiment_id, limit, offset, order_by)
- query_runs(experiment_id, query)  # e.g., "metrics.accuracy > 0.9"
- get_run_metrics(run_id)
- get_run_artifacts(run_id)
- get_artifact_content(run_id, artifact_path)
- get_best_run(experiment_id, metric)
- compare_runs(experiment_id, run_ids)
```

This solves the "agent access" problem — Claude can query experiment history without SciWeave needing to implement its own query layer.

---

## Integration Architecture

### Design Principles

1. **SciWeave owns the experiment abstraction** — the `Experiment` base class, config handling, and execution flow
2. **Backends are pluggable** — SQLite for simple/offline use, MLflow for production/collaboration
3. **Reads happen via MCP** — when using MLflow backend, agents query via MCP tools, not SciWeave's API
4. **Backward compatible** — existing SciWeave code continues to work unchanged

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AI Agent (Claude Code)                          │
│                                                                         │
│  Writes experiments:              Reads history:                        │
│  - Creates Experiment subclass    - mlflow.get_runs()                   │
│  - Calls exp()                    - mlflow.query_runs()                 │
│  - SciWeave handles logging       - mlflow.get_artifact_content()       │
└────────────────┬────────────────────────────────┬───────────────────────┘
                 │                                │
                 │ Python API                     │ MCP Protocol
                 ▼                                ▼
┌────────────────────────────────┐  ┌────────────────────────────────────┐
│          SciWeave              │  │       MLflow MCP Server            │
│                                │  │       (mlflow-mcp package)         │
│  - Experiment base class       │  │                                    │
│  - Config flattening           │  │  Exposes read-only tools:          │
│  - Backend abstraction         │  │  - get_experiments                 │
│                                │  │  - get_runs                        │
└────────────────┬───────────────┘  │  - query_runs                      │
                 │                  │  - get_artifacts                   │
                 │                  │  - compare_runs                    │
                 ▼                  └──────────────┬─────────────────────┘
┌────────────────────────────────┐                │
│      TrackingBackend (ABC)     │                │
└────────────────┬───────────────┘                │
                 │                                │
     ┌───────────┴───────────┐                    │
     ▼                       ▼                    │
┌──────────────┐    ┌──────────────┐              │
│SQLiteBackend │    │MLflowBackend │◄─────────────┘
│  (current)   │    │   (new)      │
└──────────────┘    └──────┬───────┘
                           │
                           ▼
                   ┌──────────────────┐
                   │  MLflow Server   │
                   │  (local or       │
                   │   Databricks)    │
                   └──────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `Experiment` | Define experiment structure, execute `run()`, coordinate with backend |
| `ProjectManager` | Hold backend reference, provide convenience methods |
| `SQLiteBackend` | Local storage for simple/offline use cases |
| `MLflowBackend` | Log to MLflow tracking server |
| `HybridBackend` | Log to both (local cache + remote durability) |
| MLflow MCP | Expose read API to agents |

---

## Implementation Plan

### Phase 1: Backend Abstraction

**Goal**: Extract current SQLite logic into a backend interface, enabling pluggable backends.

#### 1.1 Define Backend Protocol

```python
# sciweave/backends/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path

class TrackingBackend(ABC):
    """Abstract interface for experiment tracking backends."""
    
    @abstractmethod
    def start_run(
        self, 
        experiment_name: str, 
        config: Dict[str, Any],
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Start a new run and log config.
        
        Returns:
            run_id: Unique identifier for this run
        """
        pass
    
    @abstractmethod
    def log_results(self, results: Dict[str, Any]) -> None:
        """Log final results (scalar metrics)."""
        pass
    
    @abstractmethod
    def log_metric(
        self, 
        key: str, 
        value: float, 
        step: Optional[int] = None
    ) -> None:
        """Log a single metric, optionally with step for time-series."""
        pass
    
    @abstractmethod
    def log_artifact(self, local_path: Path, artifact_name: Optional[str] = None) -> None:
        """Log a file artifact (model, plot, data)."""
        pass
    
    @abstractmethod
    def set_status(self, status: str) -> None:
        """Set run status (running, completed, failed)."""
        pass
    
    @abstractmethod
    def end_run(self) -> None:
        """Finalize the current run."""
        pass
    
    # Query methods (optional — may delegate to MCP)
    def query(self, experiment_name: str, **kwargs) -> Any:
        """Query past runs. Optional — backends may not implement."""
        raise NotImplementedError("Use MCP for queries with this backend")
```

#### 1.2 Refactor SQLite Backend

```python
# sciweave/backends/sqlite.py

class SQLiteBackend(TrackingBackend):
    """Current SciWeave behavior, extracted into backend interface."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._current_run_id = None
        self._current_experiment = None
    
    def start_run(self, experiment_name, config, run_name=None, tags=None):
        self._current_experiment = experiment_name
        self._current_run_id = self._generate_run_id()
        self._ensure_table(experiment_name)
        self._insert_config(experiment_name, config)
        return self._current_run_id
    
    def log_results(self, results):
        self._update_row(self._current_experiment, self._current_run_id, results)
    
    def log_metric(self, key, value, step=None):
        # For SQLite, we only store final values (no time-series)
        # Could extend with a metrics table if needed
        if step is None:
            self._update_row(self._current_experiment, self._current_run_id, {key: value})
    
    def log_artifact(self, local_path, artifact_name=None):
        # Store path reference in DB
        name = artifact_name or local_path.name
        self._log_artifact_ref(self._current_run_id, name, str(local_path))
    
    def query(self, experiment_name, **kwargs):
        # Existing query implementation
        ...
```

#### 1.3 Update ProjectManager

```python
# sciweave/core.py

class ProjectManager:
    def __init__(
        self, 
        project_name: str,
        backend: str = "sqlite",  # "sqlite", "mlflow", "hybrid"
        **backend_kwargs
    ):
        self.project_name = project_name
        self.backend = self._create_backend(backend, **backend_kwargs)
    
    def _create_backend(self, backend_type: str, **kwargs) -> TrackingBackend:
        if backend_type == "sqlite":
            db_path = kwargs.get("db_path", f"{self.project_name}.db")
            return SQLiteBackend(db_path)
        elif backend_type == "mlflow":
            tracking_uri = kwargs.get("tracking_uri")
            return MLflowBackend(tracking_uri)
        elif backend_type == "hybrid":
            return HybridBackend(
                sqlite_path=kwargs.get("db_path", f"{self.project_name}.db"),
                mlflow_uri=kwargs.get("tracking_uri")
            )
        else:
            raise ValueError(f"Unknown backend: {backend_type}")
```

**Deliverables:**
- [ ] `sciweave/backends/base.py` — abstract interface
- [ ] `sciweave/backends/sqlite.py` — refactored current implementation
- [ ] Updated `ProjectManager` with backend selection
- [ ] Tests ensuring backward compatibility

**Estimated effort**: 2-3 days

---

### Phase 2: MLflow Backend

**Goal**: Implement MLflow backend for production use.

#### 2.1 Core Implementation

```python
# sciweave/backends/mlflow_backend.py

import mlflow
from mlflow.tracking import MlflowClient
from typing import Any, Dict, Optional
from pathlib import Path

class MLflowBackend(TrackingBackend):
    """Backend that logs to MLflow tracking server."""
    
    def __init__(self, tracking_uri: Optional[str] = None):
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        self._active_run = None
    
    def start_run(
        self, 
        experiment_name: str, 
        config: Dict[str, Any],
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        # Create experiment if doesn't exist
        mlflow.set_experiment(experiment_name)
        
        # Start run
        self._active_run = mlflow.start_run(run_name=run_name)
        
        # Log flattened config as params
        flat_config = self._flatten_config(config)
        mlflow.log_params(flat_config)
        
        # Log tags
        if tags:
            for key, value in tags.items():
                mlflow.set_tag(key, value)
        
        return self._active_run.info.run_id
    
    def log_results(self, results: Dict[str, Any]) -> None:
        """Log final results as metrics."""
        for key, value in results.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(key, value)
            else:
                # Non-numeric results logged as tags or artifacts
                mlflow.set_tag(f"result_{key}", str(value))
    
    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """Log metric with optional step for time-series."""
        mlflow.log_metric(key, value, step=step)
    
    def log_artifact(self, local_path: Path, artifact_name: Optional[str] = None) -> None:
        """Upload artifact to MLflow artifact store."""
        mlflow.log_artifact(str(local_path), artifact_path=artifact_name)
    
    def set_status(self, status: str) -> None:
        """Set run status via tag (MLflow manages actual status)."""
        mlflow.set_tag("sciweave.status", status)
    
    def end_run(self, status: str = "FINISHED") -> None:
        """End the active run."""
        mlflow.end_run(status=status)
        self._active_run = None
    
    def _flatten_config(self, config: Dict, prefix: str = "") -> Dict[str, str]:
        """Flatten nested config for MLflow params (which must be flat)."""
        items = {}
        for key, value in config.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                items.update(self._flatten_config(value, new_key))
            else:
                items[new_key] = str(value)
        return items
    
    def query(self, experiment_name: str, **kwargs):
        """
        Query is available but discouraged — use MCP instead.
        Provided for compatibility and non-agent use cases.
        """
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            return []
        
        filter_string = kwargs.get("filter_string", "")
        max_results = kwargs.get("max_results", 100)
        
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=filter_string,
            max_results=max_results
        )
        return runs  # Returns pandas DataFrame
```

#### 2.2 Hybrid Backend (Optional)

For users who want local speed with remote durability:

```python
# sciweave/backends/hybrid.py

class HybridBackend(TrackingBackend):
    """Write to both SQLite (fast local) and MLflow (durable remote)."""
    
    def __init__(self, sqlite_path: str, mlflow_uri: str):
        self.sqlite = SQLiteBackend(sqlite_path)
        self.mlflow = MLflowBackend(mlflow_uri)
    
    def start_run(self, experiment_name, config, **kwargs):
        # Start in both
        sqlite_id = self.sqlite.start_run(experiment_name, config, **kwargs)
        mlflow_id = self.mlflow.start_run(experiment_name, config, **kwargs)
        
        # Store mapping
        self._run_mapping = {"sqlite": sqlite_id, "mlflow": mlflow_id}
        return mlflow_id  # Return MLflow ID as canonical
    
    def log_results(self, results):
        self.sqlite.log_results(results)
        self.mlflow.log_results(results)
    
    def log_metric(self, key, value, step=None):
        self.sqlite.log_metric(key, value, step)
        self.mlflow.log_metric(key, value, step)
    
    def log_artifact(self, local_path, artifact_name=None):
        self.sqlite.log_artifact(local_path, artifact_name)
        self.mlflow.log_artifact(local_path, artifact_name)
    
    def query(self, experiment_name, **kwargs):
        # Query from local SQLite for speed
        return self.sqlite.query(experiment_name, **kwargs)
```

**Deliverables:**
- [ ] `sciweave/backends/mlflow_backend.py`
- [ ] `sciweave/backends/hybrid.py` (optional)
- [ ] Integration tests with local MLflow server
- [ ] Documentation for MLflow setup

**Estimated effort**: 3-4 days

---

### Phase 3: Enhanced Experiment Class

**Goal**: Add methods for richer logging (time-series metrics, artifacts) while preserving simple return-dict pattern.

#### 3.1 Add Logging Methods to Experiment

```python
# sciweave/experiment.py

class Experiment:
    def __init__(
        self, 
        project_manager: ProjectManager,
        experiment_name: str,
        config: Dict[str, Any],
        run_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        self.pm = project_manager
        self.experiment_name = experiment_name
        self.config = config
        self.original_config = config  # For Hydra compatibility
        self.run_name = run_name
        self.tags = tags
        self._run_id = None
    
    def __call__(self) -> Dict[str, Any]:
        """Execute experiment with tracking."""
        try:
            # Start tracking
            tag_dict = {t: "true" for t in (self.tags or [])}
            self._run_id = self.pm.backend.start_run(
                self.experiment_name,
                self.config,
                run_name=self.run_name,
                tags=tag_dict
            )
            self.pm.backend.set_status("running")
            
            # Execute user's experiment
            results = self.run()
            
            # Log results
            if results:
                self.pm.backend.log_results(results)
            
            self.pm.backend.set_status("completed")
            return results
            
        except Exception as e:
            self.pm.backend.set_status("failed")
            self.pm.backend.set_tag("error", str(e))
            raise
            
        finally:
            self.pm.backend.end_run()
    
    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Implement your experiment logic here.
        
        Returns:
            Dict of result metrics (will be logged automatically)
        """
        pass
    
    # --- Optional logging methods for use inside run() ---
    
    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """
        Log a metric during training.
        
        Use for time-series data like loss curves:
            for epoch in range(100):
                loss = train_epoch()
                self.log_metric("loss", loss, step=epoch)
        """
        self.pm.backend.log_metric(key, value, step)
    
    def log_artifact(self, path: Union[str, Path], name: Optional[str] = None) -> None:
        """
        Log a file artifact (model checkpoint, plot, data sample).
        
        Args:
            path: Local path to the file
            name: Optional name/subdirectory in artifact store
        """
        self.pm.backend.log_artifact(Path(path), name)
    
    def log_figure(self, fig, name: str) -> None:
        """
        Log a matplotlib figure as an artifact.
        
        Args:
            fig: matplotlib figure object
            name: Filename (e.g., "loss_curve.png")
        """
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            fig.savefig(f.name)
            self.log_artifact(f.name, name)
    
    def log_model(self, model, name: str = "model", **kwargs) -> None:
        """
        Log a model artifact.
        
        For MLflow backend, uses appropriate flavor (pytorch, sklearn, etc.)
        For SQLite backend, pickles the model.
        """
        self.pm.backend.log_model(model, name, **kwargs)
```

#### 3.2 Usage Example

```python
class TransformerExperiment(Experiment):
    def run(self):
        model = create_model(self.config["model"])
        optimizer = create_optimizer(model, self.config["training"])
        
        for epoch in range(self.config["training"]["epochs"]):
            train_loss = train_epoch(model, optimizer, train_loader)
            val_loss = evaluate(model, val_loader)
            
            # Log time-series metrics
            self.log_metric("train_loss", train_loss, step=epoch)
            self.log_metric("val_loss", val_loss, step=epoch)
            
            # Save checkpoint periodically
            if epoch % 10 == 0:
                torch.save(model.state_dict(), f"checkpoint_{epoch}.pt")
                self.log_artifact(f"checkpoint_{epoch}.pt")
        
        # Log final model
        self.log_model(model, "final_model")
        
        # Log analysis plots
        fig = plot_loss_curves(train_losses, val_losses)
        self.log_figure(fig, "loss_curves.png")
        
        # Return final metrics (logged automatically)
        return {
            "final_train_loss": train_loss,
            "final_val_loss": val_loss,
            "best_epoch": best_epoch
        }
```

**Deliverables:**
- [ ] Updated `Experiment` class with logging methods
- [ ] `log_model` implementation for each backend
- [ ] Documentation and examples
- [ ] Tests for new logging methods

**Estimated effort**: 2-3 days

---

### Phase 4: MCP Integration Documentation

**Goal**: Document how to set up MLflow MCP for agent access.

#### 4.1 MCP Setup Guide

Create `docs/mcp_setup.md`:

```markdown
# Using SciWeave with AI Agents (MCP)

SciWeave + MLflow + MCP enables AI agents like Claude Code to:
- Query your experiment history
- Compare runs
- Retrieve artifacts
- Make informed decisions about next experiments

## Setup

### 1. Install MLflow MCP Server

```bash
pip install mlflow-mcp
```

### 2. Configure Your AI Agent

**Claude Code** (`.mcp.json` in project root):
```json
{
  "mcpServers": {
    "mlflow": {
      "command": "uvx",
      "args": ["mlflow-mcp"],
      "env": {
        "MLFLOW_TRACKING_URI": "http://localhost:5000"
      }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "mlflow": {
      "command": "uvx", 
      "args": ["mlflow-mcp"],
      "env": {
        "MLFLOW_TRACKING_URI": "http://localhost:5000"
      }
    }
  }
}
```

### 3. Start MLflow Server

```bash
mlflow server --host 0.0.0.0 --port 5000
```

### 4. Configure SciWeave

```python
from sciweave import ProjectManager, Experiment

pm = ProjectManager(
    "my_project",
    backend="mlflow",
    tracking_uri="http://localhost:5000"
)
```

## Agent Workflow

Once configured, your AI agent can:

**Query past runs:**
> "What experiments have I run for belief-state-geometry?"

**Find best configurations:**
> "What config gave the best accuracy in experiment X?"

**Compare runs:**
> "Compare the last 5 runs — what changed?"

**Retrieve artifacts:**
> "Show me the loss curve from run abc123"

**Plan next experiment:**
> "Based on past runs, what learning rate should I try next?"
```

**Deliverables:**
- [ ] `docs/mcp_setup.md` — setup guide
- [ ] `docs/agent_workflow.md` — example workflows
- [ ] Example `.mcp.json` configs for common agents
- [ ] Troubleshooting guide

**Estimated effort**: 1-2 days

---

### Phase 5: Testing & Validation

**Goal**: Ensure reliability across backends and use cases.

#### 5.1 Test Matrix

| Test Category | SQLite | MLflow | Hybrid |
|--------------|--------|--------|--------|
| Basic run tracking | ✓ | ✓ | ✓ |
| Config flattening | ✓ | ✓ | ✓ |
| Result logging | ✓ | ✓ | ✓ |
| Time-series metrics | ✓ | ✓ | ✓ |
| Artifact logging | ✓ | ✓ | ✓ |
| Error handling | ✓ | ✓ | ✓ |
| Schema evolution | ✓ | N/A | ✓ |
| Hydra configs | ✓ | ✓ | ✓ |
| Query API | ✓ | ✓ | ✓ |

#### 5.2 Integration Tests

```python
# tests/test_mlflow_integration.py

import pytest
import mlflow
from sciweave import ProjectManager, Experiment

@pytest.fixture
def mlflow_server():
    """Start local MLflow server for testing."""
    # Use mlflow's built-in test utilities or a temp directory
    mlflow.set_tracking_uri("sqlite:///test_mlflow.db")
    yield
    # Cleanup

def test_basic_experiment_tracking(mlflow_server):
    pm = ProjectManager("test", backend="mlflow")
    
    class TestExp(Experiment):
        def run(self):
            return {"accuracy": 0.95}
    
    exp = TestExp(pm, "test_experiment", {"lr": 0.001})
    results = exp()
    
    assert results["accuracy"] == 0.95
    
    # Verify in MLflow
    runs = mlflow.search_runs(experiment_names=["test_experiment"])
    assert len(runs) == 1
    assert runs.iloc[0]["params.lr"] == "0.001"
    assert runs.iloc[0]["metrics.accuracy"] == 0.95

def test_time_series_metrics(mlflow_server):
    pm = ProjectManager("test", backend="mlflow")
    
    class TrainingExp(Experiment):
        def run(self):
            for step in range(10):
                self.log_metric("loss", 1.0 / (step + 1), step=step)
            return {"final_loss": 0.1}
    
    exp = TrainingExp(pm, "training_exp", {})
    exp()
    
    # Verify metric history
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(experiment_names=["training_exp"])
    run_id = runs[0].info.run_id
    history = client.get_metric_history(run_id, "loss")
    assert len(history) == 10
```

**Deliverables:**
- [ ] Unit tests for each backend
- [ ] Integration tests with MLflow
- [ ] End-to-end test with MCP (manual verification)
- [ ] CI/CD pipeline configuration

**Estimated effort**: 2-3 days

---

## Timeline Summary

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Backend Abstraction | 2-3 days | None |
| 2 | MLflow Backend | 3-4 days | Phase 1 |
| 3 | Enhanced Experiment Class | 2-3 days | Phase 1 |
| 4 | MCP Documentation | 1-2 days | Phase 2 |
| 5 | Testing & Validation | 2-3 days | Phases 1-3 |

**Total estimated effort**: 10-15 days

Phases 2 and 3 can be parallelized after Phase 1 is complete.

---

## API Summary

### After Integration

```python
from sciweave import ProjectManager, Experiment

# Option 1: Local-only (current behavior)
pm = ProjectManager("my_project")  # SQLite backend

# Option 2: MLflow backend (for collaboration + MCP access)
pm = ProjectManager(
    "my_project",
    backend="mlflow",
    tracking_uri="http://localhost:5000"
)

# Option 3: Hybrid (local speed + remote durability)
pm = ProjectManager(
    "my_project", 
    backend="hybrid",
    tracking_uri="http://localhost:5000"
)

# Experiment definition unchanged
class MyExperiment(Experiment):
    def run(self):
        for epoch in range(100):
            loss = train_epoch()
            self.log_metric("loss", loss, step=epoch)  # NEW: time-series
        
        self.log_artifact("model.pt")  # NEW: artifacts
        
        return {"final_loss": loss}

exp = MyExperiment(pm, "experiment_name", config)
results = exp()
```

### Agent Access (via MCP)

```
Claude: "What configs have I tried for experiment X?"
→ Uses mlflow.get_runs(experiment_id="X")

Claude: "Show me the loss curve from the best run"  
→ Uses mlflow.get_best_run() + mlflow.get_artifact_content()

Claude: "Compare runs abc and def"
→ Uses mlflow.compare_runs()
```

---

## Open Questions

1. **Model logging abstraction**: Should `log_model()` auto-detect framework (PyTorch, sklearn, etc.) or require explicit specification?

2. **Artifact retrieval**: Should SciWeave provide `get_artifact()` for non-MCP use cases, or leave that entirely to MCP/MLflow client?

3. **Query API deprecation**: With MCP handling reads, should we deprecate SciWeave's query API for MLflow backend, or keep it for non-agent use?

4. **Databricks integration**: Any special handling needed for Databricks-hosted MLflow? (Auth, Unity Catalog, etc.)

5. **Offline-to-online sync**: If someone starts with SQLite and wants to migrate to MLflow, should we provide a migration tool?

---

## Success Criteria

1. **Backward compatible**: Existing SciWeave code works unchanged
2. **Agent-friendly**: Claude Code can query experiment history via MCP
3. **Zero-config local**: SQLite backend requires no setup
4. **Production-ready MLflow**: Full feature parity with MLflow tracking API
5. **Documented**: Clear guides for each backend and MCP setup
6. **Tested**: >90% coverage on core functionality