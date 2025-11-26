"""
SciWeave - Lightweight experiment tracking for scientific research.

A flexible framework that automatically captures experiment configurations
and results in a local SQLite database.
"""

from sciweave.project_manager import ProjectManager
from sciweave.experiment import Experiment

__version__ = "0.1.0"
__all__ = ["ProjectManager", "Experiment"]
