"""Project management for SciWeave - thin wrapper around MLflow experiments."""

import mlflow


class Project:
    """
    Thin wrapper around MLflow experiment management.

    A Project represents a collection of related experiments, mapped to
    MLflow experiments with a common prefix.

    Example:
        project = Project("belief-state-geometry", tracking_uri="databricks")
        # Creates MLflow experiments like "belief-state-geometry/transformer_v1"
    """

    def __init__(self, name: str, tracking_uri: str = "databricks"):
        """
        Initialize a project connected to an MLflow tracking server.

        Args:
            name: Project name, used as prefix for MLflow experiments
            tracking_uri: MLflow tracking URI. Options:
                - "databricks": Use Databricks MLflow (requires DATABRICKS_HOST and
                  DATABRICKS_TOKEN environment variables)
                - "http://host:port": Connect to a remote MLflow server
                - Local path: Use local file-based tracking (e.g., "./mlruns")
        """
        self.name = name
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    def get_or_create_experiment(self, experiment_name: str) -> str:
        """
        Get or create an MLflow experiment.

        Args:
            experiment_name: Name of the experiment (will be prefixed with project name)

        Returns:
            MLflow experiment ID
        """
        full_name = f"{self.name}/{experiment_name}"
        experiment = mlflow.get_experiment_by_name(full_name)
        if experiment is None:
            return mlflow.create_experiment(full_name)
        return experiment.experiment_id

    def __repr__(self) -> str:
        return f"Project(name='{self.name}', tracking_uri='{self.tracking_uri}')"
