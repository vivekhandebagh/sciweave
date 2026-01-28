#!/usr/bin/env python3
"""
Comprehensive demo of SciWeave framework capabilities.

This script demonstrates:
- Creating experiments with the Project/Experiment pattern
- Logging time-series metrics during training
- Logging artifacts (models, plots)
- Using tags for organization
- Config flattening for MLflow params

Requirements:
- MLflow server running (or use local file tracking)
- Set MLFLOW_TRACKING_URI environment variable

Usage:
    # With local file tracking (no server needed)
    python example_demo.py

    # With MLflow server
    export MLFLOW_TRACKING_URI=http://localhost:5000
    python example_demo.py

    # With Databricks
    export MLFLOW_TRACKING_URI=databricks
    export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
    export DATABRICKS_TOKEN=your-token
    python example_demo.py
"""

import os
import random
import tempfile
from typing import Dict, Any

# Use local file tracking if no URI set
if not os.environ.get("MLFLOW_TRACKING_URI"):
    os.environ["MLFLOW_TRACKING_URI"] = "./mlruns"

from sciweave import Project, Experiment


# ==============================================================================
# Define Different Types of Experiments
# ==============================================================================

class OptimizationExperiment(Experiment):
    """Simulates an optimization problem with time-series metrics."""

    def run(self) -> Dict[str, Any]:
        lr = self.config.get('learning_rate', 0.01)
        iterations = self.config.get('iterations', 100)
        momentum = self.config.get('momentum', 0.0)

        # Simulate optimization with time-series logging
        loss = 1.0
        for step in range(iterations):
            # Simulate loss decrease with noise
            loss = loss * (1 - lr * (1 + momentum)) + random.gauss(0, 0.01)
            loss = max(0.01, loss)

            # Log time-series metric
            if step % 10 == 0:
                self.log_metric("loss", loss, step=step)

        return {
            'final_loss': round(loss, 4),
            'converged': loss < 0.5,
        }


class MLModelExperiment(Experiment):
    """Simulates training a machine learning model."""

    def run(self) -> Dict[str, Any]:
        model_type = self.config.get('model', 'linear')
        lr = self.config.get('learning_rate', 0.001)
        batch_size = self.config.get('batch_size', 32)
        epochs = self.config.get('epochs', 10)

        # Simulate training
        if model_type == 'neural_net':
            base_acc = 0.85
        elif model_type == 'random_forest':
            base_acc = 0.80
        else:
            base_acc = 0.75

        # Training loop with time-series logging
        for epoch in range(epochs):
            # Simulate accuracy improvement
            accuracy = min(0.99, base_acc + (epoch / epochs) * 0.1 + random.gauss(0, 0.02))
            train_loss = 1 - accuracy + random.gauss(0, 0.01)

            self.log_metric("train_accuracy", accuracy, step=epoch)
            self.log_metric("train_loss", train_loss, step=epoch)

        # Simulate saving a model artifact
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"Model: {model_type}\n")
            f.write(f"Final accuracy: {accuracy}\n")
            model_path = f.name

        self.log_artifact(model_path, "model")
        os.unlink(model_path)  # Clean up temp file

        return {
            'accuracy': round(accuracy, 4),
            'val_accuracy': round(accuracy - random.uniform(0.01, 0.05), 4),
            'final_loss': round(train_loss, 4),
        }


class SimulationExperiment(Experiment):
    """Simulates a physics simulation with nested config."""

    def run(self) -> Dict[str, Any]:
        # Access nested config (flattened for MLflow params)
        timestep = self.config.get('simulation.timestep', 0.01)
        particles = self.config.get('simulation.num_particles', 1000)
        temperature = self.config.get('physics.temperature', 300)

        # Simulate physics
        energy = particles * temperature * 1.38e-23
        stability = 1.0 / (1 + timestep * 10)

        return {
            'total_energy': round(energy * 1e20, 2),
            'stability_score': round(stability, 3),
            'simulation_time': round(random.uniform(0.5, 5.0), 2),
        }


# ==============================================================================
# Main Demo Script
# ==============================================================================

def main():
    print("=" * 80)
    print("SCIWEAVE FRAMEWORK DEMO (MLflow Backend)")
    print("=" * 80)

    # Initialize project
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "./mlruns")
    print(f"\n📁 Initializing project 'research_demo'...")
    print(f"   Tracking URI: {tracking_uri}")
    project = Project("research_demo", tracking_uri=tracking_uri)

    # ==============================================================================
    # PART 1: Basic Experiments with Time-Series Metrics
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 1: Running Optimization Experiments")
    print("=" * 80)

    print("\n🔬 Running optimization experiments with time-series logging...")
    for lr in [0.01, 0.05, 0.1]:
        config = {
            'learning_rate': lr,
            'iterations': 100,
            'momentum': 0.9,
            'algorithm': 'sgd',
        }
        exp = OptimizationExperiment(
            project,
            "optimization_study",
            config,
            run_name=f"lr_{lr}",
            tags={'sweep': 'learning_rate'}
        )
        result = exp()
        print(f"  LR={lr} -> final_loss={result['final_loss']}, converged={result['converged']}")

    # ==============================================================================
    # PART 2: ML Model Training with Artifacts
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 2: ML Model Training with Artifact Logging")
    print("=" * 80)

    print("\n🤖 Training ML models...")
    for model_type in ['linear', 'neural_net', 'random_forest']:
        config = {
            'model': model_type,
            'learning_rate': 0.01,
            'batch_size': 32,
            'epochs': 20,
        }
        exp = MLModelExperiment(
            project,
            "model_comparison",
            config,
            run_name=f"{model_type}_baseline",
            tags={'model_type': model_type, 'version': 'v1'}
        )
        result = exp()
        print(f"  {model_type}: accuracy={result['accuracy']}, val_accuracy={result['val_accuracy']}")

    # ==============================================================================
    # PART 3: Nested Config with Flattening
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 3: Nested Config (Automatic Flattening)")
    print("=" * 80)

    print("\n🌊 Running simulation with nested config...")
    config = {
        'simulation': {
            'timestep': 0.01,
            'num_particles': 5000,
            'duration': 100,
        },
        'physics': {
            'temperature': 300,
            'pressure': 1.0,
        },
        'output': {
            'save_every': 10,
            'format': 'hdf5',
        }
    }
    exp = SimulationExperiment(
        project,
        "particle_simulation",
        config,
        run_name="baseline_simulation",
        tags={'system': 'particles', 'complexity': 'medium'}
    )
    result = exp()
    print(f"  Results: energy={result['total_energy']}, stability={result['stability_score']}")
    print(f"  Note: Nested config 'simulation.timestep' logged as MLflow param")

    # ==============================================================================
    # Summary
    # ==============================================================================
    print("\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("=" * 80)

    print("\n📊 To view results:")
    if tracking_uri.startswith("./"):
        print(f"   1. Run: mlflow ui --backend-store-uri {tracking_uri}")
        print("   2. Open: http://localhost:5000")
    elif tracking_uri == "databricks":
        print("   1. Go to your Databricks workspace")
        print("   2. Navigate to MLflow Experiments")
    else:
        print(f"   Open: {tracking_uri}")

    print("\n📡 To query via MCP (with sciweave-mcp server):")
    print("   - list_experiments() -> shows 'research_demo/*' experiments")
    print("   - get_latest_run('research_demo/model_comparison') -> last run details")
    print("   - get_metric_history(run_id, 'train_loss') -> training curve")
    print("   - compare_runs('run_id1,run_id2,run_id3') -> side-by-side comparison")


if __name__ == "__main__":
    main()
