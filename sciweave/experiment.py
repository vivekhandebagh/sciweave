"""Experiment base class for SciWeave - structured experiment scaffolding."""

import mlflow
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .project import Project
from .config import flatten_config


class Experiment(ABC):
    """
    Base class for structured experiments.

    Subclass and implement run() to define your experiment.
    Results returned from run() are automatically logged to MLflow.

    Example:
        class MyExperiment(Experiment):
            def run(self):
                model = train_model(self.config)
                return {"accuracy": evaluate(model)}

        project = Project("my-project", tracking_uri="databricks")
        exp = MyExperiment(project, "experiment_v1", {"lr": 0.01, "epochs": 100})
        results = exp()  # Runs and logs to MLflow
    """

    def __init__(
        self,
        project: Project,
        experiment_name: str,
        config: Dict[str, Any],
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize an experiment.

        Args:
            project: Project instance connected to MLflow
            experiment_name: Name for this experiment (will be prefixed with project name)
            config: Configuration dictionary (can be nested)
            run_name: Optional name for this specific run
            tags: Optional tags to attach to the run
        """
        self.project = project
        self.experiment_name = experiment_name
        self.config = config  # Original nested config for use in run()
        self.run_name = run_name
        self.tags = tags or {}

        # Flatten config for MLflow params
        self._flat_config = flatten_config(config)

        # Get/create MLflow experiment
        self._experiment_id = project.get_or_create_experiment(experiment_name)

        # Run state
        self._active_run = None
        self._run_id = None

    def __call__(self) -> Dict[str, Any]:
        """
        Execute the experiment with full MLflow tracking.

        Returns:
            Results dictionary from run()
        """
        try:
            # Start MLflow run
            mlflow.set_experiment(experiment_id=self._experiment_id)
            self._active_run = mlflow.start_run(run_name=self.run_name)
            self._run_id = self._active_run.info.run_id

            # Log config as params
            mlflow.log_params(self._flat_config)

            # Log tags
            for key, value in self.tags.items():
                mlflow.set_tag(key, value)
            mlflow.set_tag("status", "running")

            # Run the experiment
            results = self.run()

            # Log results
            if results:
                for key, value in results.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value)
                    else:
                        mlflow.set_tag(f"result.{key}", str(value))

            mlflow.set_tag("status", "completed")
            mlflow.end_run(status="FINISHED")
            return results

        except Exception as e:
            mlflow.set_tag("status", "failed")
            mlflow.set_tag("error", str(e))
            mlflow.end_run(status="FAILED")
            raise

        finally:
            self._active_run = None

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Implement your experiment logic here.

        Access config via self.config (original nested structure).
        Use self.log_metric() for time-series metrics during training.
        Use self.log_artifact() for files (models, plots, data).

        Returns:
            Dict of final results (automatically logged as metrics/tags)
        """
        pass

    def log_metric(
        self, key: str, value: float, step: Optional[int] = None
    ) -> None:
        """
        Log a metric during training.

        Use this for time-series data like loss curves:
            for epoch in range(100):
                loss = train_epoch()
                self.log_metric("loss", loss, step=epoch)

        Args:
            key: Metric name
            value: Metric value (must be numeric)
            step: Optional step number for time-series
        """
        mlflow.log_metric(key, value, step=step)

    def log_metrics(
        self, metrics: Dict[str, float], step: Optional[int] = None
    ) -> None:
        """
        Log multiple metrics at once.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number for time-series
        """
        mlflow.log_metrics(metrics, step=step)

    def log_artifact(
        self, local_path: Union[str, Path], artifact_path: Optional[str] = None
    ) -> None:
        """
        Log a file artifact.

        Args:
            local_path: Path to the local file
            artifact_path: Optional subdirectory in the artifact store
        """
        mlflow.log_artifact(str(local_path), artifact_path)

    def log_artifacts(
        self, local_dir: Union[str, Path], artifact_path: Optional[str] = None
    ) -> None:
        """
        Log all files in a directory as artifacts.

        Args:
            local_dir: Path to local directory
            artifact_path: Optional subdirectory in the artifact store
        """
        mlflow.log_artifacts(str(local_dir), artifact_path)

    def log_figure(self, figure: Any, filename: str) -> None:
        """
        Log a matplotlib figure.

        Args:
            figure: Matplotlib figure object
            filename: Filename for the figure (e.g., "loss_curve.png")
        """
        mlflow.log_figure(figure, filename)

    def log_dict(self, dictionary: Dict[str, Any], filename: str) -> None:
        """
        Log a dictionary as a JSON or YAML artifact.

        Args:
            dictionary: Dictionary to log
            filename: Filename (e.g., "config.json" or "results.yaml")
        """
        mlflow.log_dict(dictionary, filename)

    def set_tag(self, key: str, value: str) -> None:
        """
        Set a tag on the current run.

        Args:
            key: Tag name
            value: Tag value
        """
        mlflow.set_tag(key, value)

    @property
    def run_id(self) -> Optional[str]:
        """Get the current run ID (available during run execution)."""
        return self._run_id

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"experiment='{self.experiment_name}', "
            f"config={self.config})"
        )
