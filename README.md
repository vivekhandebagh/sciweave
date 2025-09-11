# SciWeave

A lightweight, flexible experiment tracking framework for machine learning research. SciWeave automatically captures experiment configurations and results in a local SQLite database, making it easy to track, query, and compare ML experiments without external dependencies or complex setup.

## 🎯 Problem It Solves

Machine learning researchers often struggle with:
- **Lost experiments**: Running hundreds of experiments but losing track of what worked
- **Config chaos**: Forgetting which hyperparameters produced which results  
- **Comparison difficulty**: Hard to query and compare runs across different experiments
- **Overly complex tools**: Existing solutions require servers, accounts, or complex setup
- **Schema rigidity**: Fixed schemas that don't adapt to evolving experiments

SciWeave solves these problems with a simple, local-first approach that grows with your research.

## ✨ Key Features

- **🔌 Simple Integration**: Subclass `Experiment`, implement `run()`, and you're done
- **📊 Automatic Tracking**: Configs and results automatically saved to SQLite database
- **🔍 Powerful Queries**: Query by config values, time ranges, tags, or any custom field
- **📈 Schema Evolution**: Automatically adapts to new config parameters and result fields
- **🏷️ Flexible Tagging**: Tag and annotate runs for easy organization
- **🔗 Hydra Compatible**: Works seamlessly with Hydra configs or plain Python dicts
- **💾 Local Storage**: No external dependencies, servers, or accounts needed
- **🚀 Fast & Lightweight**: Pure Python with SQLite backend

## 📦 Installation

```bash
# From TestPyPI (for now)
pip install -i https://test.pypi.org/simple/ sciweave

# Or install from source
git clone https://github.com/yourusername/sciweave.git
cd sciweave
pip install -e .
```

## 🚀 Quick Start

### Basic Usage

```python
import sciweave
from sciweave import ProjectManager, Experiment

# Initialize project (creates/loads my_project.db)
pm = ProjectManager("my_project")

# Define your experiment
class MyExperiment(Experiment):
    def run(self):
        # Your experiment logic here
        accuracy = train_model(self.config['learning_rate'])
        return {"accuracy": accuracy, "loss": 0.23}

# Run experiment with config
config = {
    "learning_rate": 0.001,
    "batch_size": 32,
    "model": "resnet18"
}

exp = MyExperiment(pm, "image_classification", config)
results = exp()  # Automatically tracked in database
```

### Query Past Experiments

```python
# Find all runs with accuracy > 0.9
good_runs = pm.query(
    "image_classification",
    filters={"accuracy": ">0.9"},
    targets="all"  # Return all columns
)

# Get runs from last week
recent = pm.query(
    "image_classification", 
    time_range="week"
)

# Find specific config
specific = pm.query(
    "image_classification",
    filters={"learning_rate": 0.001, "model": "resnet18"}
)
```

### Advanced Features

```python
# Tag your runs
pm.add_tags("image_classification", run_id, ["baseline", "best"])

# Add notes
pm.add_notes("image_classification", run_id, "This run used augmentation")

# Get experiment summary
summary = pm.get_experiment_summary("image_classification")
print(f"Total runs: {summary['total_runs']}")
print(f"Success rate: {summary['status_counts']['completed'] / summary['total_runs']}")

# Find best runs
best = pm.get_best_runs("image_classification", metric="accuracy", n=5)
```

### Hydra Integration

```python
import hydra
from omegaconf import DictConfig

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig):
    pm = ProjectManager("my_project")
    
    class MyExperiment(Experiment):
        def run(self):
            # Access nested config naturally
            model = create_model(self.original_config.model)
            results = train(model, self.original_config.training)
            return results
    
    exp = MyExperiment(pm, cfg.experiment.name, cfg)
    exp()

if __name__ == "__main__":
    main()
```

## 🏗️ How It Works

1. **ProjectManager** creates a SQLite database for your project
2. Each **Experiment** gets its own table with automatic schema management
3. Configs are flattened and stored as columns for easy querying
4. Results are added as new columns dynamically
5. Every run is tracked with metadata (timestamp, status, run_id)

## 📊 Database Schema

Each experiment table automatically includes:
- `run_id`: Unique identifier for each run
- `time_stamp`: When the run started
- `experiment_name`: Name of the experiment
- `run_status`: started/running/completed/failed
- `mode`: dev/prod
- `tags`: Comma-separated tags
- `notes`: Free-form notes
- Your config parameters as columns
- Your result metrics as columns

## 🔧 Configuration

SciWeave works with:
- Plain Python dictionaries
- Nested dictionaries (automatically flattened)
- Hydra/OmegaConf DictConfigs
- Any JSON-serializable config

## 📈 Experiment Evolution

As your experiments evolve, SciWeave adapts:

```python
# First version - simple
exp = MyExperiment(pm, "test", {"lr": 0.01})
exp()  # Returns {"accuracy": 0.9}

# Later - add more metrics without changing schema
exp = MyExperiment(pm, "test", {"lr": 0.01, "momentum": 0.9})
exp()  # Returns {"accuracy": 0.92, "f1_score": 0.91}
# New columns automatically added!
```

## 🤝 Contributing

Contributions are welcome! This is an early release and we're actively looking for feedback.

## 📝 License

MIT License - see LICENSE file

## 🚧 Status

This is an early release (v0.0.1). The API may change in future versions. We recommend pinning your version for production use.

## 🔮 Roadmap

- [ ] Web dashboard for visualization
- [ ] Export to common formats (CSV, Pandas, Weights & Biases)
- [ ] Distributed experiment support
- [ ] Artifact storage (models, plots)
- [ ] Comparison tools
- [ ] Statistical analysis utilities

## 💬 Support

- Issues: [GitHub Issues](https://github.com/yourusername/sciweave/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/sciweave/discussions)

---

Built with ❤️ for ML researchers who want simple, effective experiment tracking.