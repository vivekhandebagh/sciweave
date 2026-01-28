"""Experiment spec schema for SciWeave."""

from typing import Any, Optional

import yaml
from pydantic import BaseModel


class FieldSchema(BaseModel):
    """Schema for a config or result field."""
    type: str  # TEXT, INTEGER, REAL, BOOLEAN
    description: str
    default: Optional[Any] = None
    example: Optional[Any] = None


class Hypothesis(BaseModel):
    """Experiment hypothesis structure."""
    statement: str
    prediction: str
    null_hypothesis: str
    success_criteria: Optional[str] = None


class ExperimentSpec(BaseModel):
    """Structured experiment specification."""
    title: str
    source: str  # Path to original proposal
    status: str = "pending_review"

    motivation: str

    hypothesis: Optional[Hypothesis] = None

    config: dict[str, FieldSchema] = {}
    results: dict[str, FieldSchema] = {}

    dependencies: list[str] = []
    estimated_time: Optional[str] = None
    implementation_notes: Optional[str] = None

    def to_yaml(self) -> str:
        """Convert spec to YAML string."""
        return yaml.dump(
            self.model_dump(exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ExperimentSpec":
        """Parse spec from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls(**data)

    @classmethod
    def from_file(cls, path: str) -> "ExperimentSpec":
        """Load spec from YAML file."""
        with open(path) as f:
            return cls.from_yaml(f.read())
