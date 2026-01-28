"""Tests for SciWeave MLflow integration."""

import pytest
import tempfile
import os
from pathlib import Path

import mlflow

from sciweave import Project, Experiment, flatten_config


class TestFlattenConfig:
    """Tests for config flattening utility."""

    def test_flat_config_unchanged(self):
        config = {"lr": 0.01, "epochs": 100}
        result = flatten_config(config)
        assert result == {"lr": "0.01", "epochs": "100"}

    def test_nested_config(self):
        config = {"model": {"hidden_size": 256, "layers": 4}}
        result = flatten_config(config)
        assert result == {"model.hidden_size": "256", "model.layers": "4"}

    def test_deeply_nested_config(self):
        config = {"training": {"optimizer": {"lr": 0.01, "momentum": 0.9}}}
        result = flatten_config(config)
        assert result == {
            "training.optimizer.lr": "0.01",
            "training.optimizer.momentum": "0.9",
        }

    def test_list_values(self):
        config = {"layers": [64, 32, 16]}
        result = flatten_config(config)
        assert result == {"layers": "[64, 32, 16]"}

    def test_mixed_config(self):
        config = {
            "model": {"hidden_size": 256},
            "lr": 0.01,
            "tags": ["experiment", "v1"],
        }
        result = flatten_config(config)
        assert result == {
            "model.hidden_size": "256",
            "lr": "0.01",
            "tags": '["experiment", "v1"]',
        }


class TestProject:
    """Tests for Project class."""

    def test_project_creation(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test-project", tracking_uri=tracking_uri)
        assert project.name == "test-project"
        assert project.tracking_uri == tracking_uri

    def test_get_or_create_experiment(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test-project", tracking_uri=tracking_uri)

        # First call creates experiment
        exp_id1 = project.get_or_create_experiment("exp1")
        assert exp_id1 is not None

        # Second call returns same ID
        exp_id2 = project.get_or_create_experiment("exp1")
        assert exp_id1 == exp_id2

    def test_experiment_naming(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("my-project", tracking_uri=tracking_uri)
        project.get_or_create_experiment("transformer_v1")

        # Verify experiment was created with full name
        experiment = mlflow.get_experiment_by_name("my-project/transformer_v1")
        assert experiment is not None


class TestExperiment:
    """Tests for Experiment class."""

    def test_simple_experiment(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class SimpleExperiment(Experiment):
            def run(self):
                return {"accuracy": 0.95, "loss": 0.05}

        exp = SimpleExperiment(project, "simple", {"lr": 0.01})
        results = exp()

        assert results == {"accuracy": 0.95, "loss": 0.05}

    def test_config_access_in_run(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class ConfigExperiment(Experiment):
            def run(self):
                # Access nested config
                lr = self.config["training"]["lr"]
                return {"lr_used": lr}

        config = {"training": {"lr": 0.001, "epochs": 10}}
        exp = ConfigExperiment(project, "config_test", config)
        results = exp()

        assert results == {"lr_used": 0.001}

    def test_log_metric_during_run(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class TrainingExperiment(Experiment):
            def run(self):
                for step in range(5):
                    self.log_metric("loss", 1.0 / (step + 1), step=step)
                return {"final_loss": 0.2}

        exp = TrainingExperiment(project, "training", {"epochs": 5})
        results = exp()

        assert results == {"final_loss": 0.2}

    def test_log_artifact(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        # Create a temp file to log
        artifact_file = tmp_path / "model.txt"
        artifact_file.write_text("test model content")

        class ArtifactExperiment(Experiment):
            def run(self):
                self.log_artifact(artifact_file)
                return {"saved": True}

        exp = ArtifactExperiment(project, "artifact_test", {})
        results = exp()

        assert results == {"saved": True}

    def test_experiment_with_tags(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class TaggedExperiment(Experiment):
            def run(self):
                return {"value": 1}

        exp = TaggedExperiment(
            project,
            "tagged",
            {"param": "value"},
            tags={"version": "v1", "team": "research"},
        )
        exp()

        # Tags should be logged (verified by MLflow tracking)

    def test_experiment_failure_handling(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class FailingExperiment(Experiment):
            def run(self):
                raise ValueError("Experiment failed!")

        exp = FailingExperiment(project, "failing", {})

        with pytest.raises(ValueError, match="Experiment failed!"):
            exp()

        # Run should be marked as failed in MLflow

    def test_run_name(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class NamedExperiment(Experiment):
            def run(self):
                return {}

        exp = NamedExperiment(
            project, "named_exp", {}, run_name="my-specific-run"
        )
        exp()

    def test_non_numeric_results(self, tmp_path):
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("test", tracking_uri=tracking_uri)

        class MixedResultsExperiment(Experiment):
            def run(self):
                return {
                    "accuracy": 0.95,  # Numeric -> metric
                    "model_type": "transformer",  # String -> tag
                    "best_epoch": 42,  # Numeric -> metric
                }

        exp = MixedResultsExperiment(project, "mixed", {})
        results = exp()

        assert results["accuracy"] == 0.95
        assert results["model_type"] == "transformer"
        assert results["best_epoch"] == 42


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow(self, tmp_path):
        """Test a realistic experiment workflow."""
        tracking_uri = str(tmp_path / "mlruns")
        project = Project("ml-research", tracking_uri=tracking_uri)

        class TrainingExperiment(Experiment):
            def run(self):
                config = self.config

                # Simulate training loop
                losses = []
                for epoch in range(config["epochs"]):
                    loss = 1.0 / (epoch + 1)
                    losses.append(loss)
                    self.log_metric("train_loss", loss, step=epoch)
                    self.log_metric("val_loss", loss * 1.1, step=epoch)

                final_accuracy = 0.9 + 0.01 * config["epochs"]

                return {
                    "final_loss": losses[-1],
                    "accuracy": final_accuracy,
                    "epochs_completed": config["epochs"],
                }

        config = {
            "model": {"hidden_size": 256, "num_layers": 4},
            "training": {"lr": 0.001, "batch_size": 32},
            "epochs": 5,
        }

        exp = TrainingExperiment(
            project,
            "transformer_experiment",
            config,
            run_name="baseline-run",
            tags={"version": "v1"},
        )

        results = exp()

        assert results["epochs_completed"] == 5
        assert results["accuracy"] == pytest.approx(0.95)
        assert results["final_loss"] == pytest.approx(0.2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
