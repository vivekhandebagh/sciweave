"""
SciWeave - Structured experiment scaffolding for ML research teams.

A lightweight framework that provides structure for experiments
and logs directly to MLflow/Databricks.
"""

from sciweave.project import Project
from sciweave.experiment import Experiment
from sciweave.config import flatten_config

__version__ = "0.2.0"
__all__ = ["Project", "Experiment", "flatten_config"]
