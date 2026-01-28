"""Scaffold tools for creating experiment boilerplate."""

import ast
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from sciweave_mcp.config import get_config


class ScaffoldResult(BaseModel):
    """Result of scaffolding an experiment."""
    experiment_path: str
    python_file: str
    spec_file: str
    journal_file: str
    message: str


class ValidationResult(BaseModel):
    """Result of validating an experiment."""
    valid: bool
    errors: list[str]
    warnings: list[str]


def _to_class_name(title: str) -> str:
    """Convert title to PascalCase class name."""
    # Remove all non-alphanumeric characters except spaces
    clean = re.sub(r"[^\w\s]", "", title)
    # Split on whitespace and underscores
    words = re.split(r"[\s_]+", clean)
    # Capitalize each word and join
    return "".join(word.capitalize() for word in words if word)


def _to_snake_case(title: str) -> str:
    """Convert title to snake_case."""
    # Remove special characters except spaces and dashes
    clean = re.sub(r"[^\w\s\-]", "", title)
    # Split on spaces/dashes
    words = re.split(r"[\s\-]+", clean.lower())
    return "_".join(word for word in words if word)


def _generate_config_docstring(config: dict[str, dict]) -> str:
    """Generate config parameter documentation."""
    lines = []
    for name, field in config.items():
        default_str = f" (default: {field.get('default')})" if field.get('default') is not None else ""
        lines.append(f"        - {name} ({field.get('type', 'TEXT')}): {field.get('description', '')}{default_str}")
    return "\n".join(lines) if lines else "        (none defined)"


def _generate_results_docstring(results: dict[str, dict]) -> str:
    """Generate results parameter documentation."""
    lines = []
    for name, field in results.items():
        lines.append(f"        - {name} ({field.get('type', 'REAL')}): {field.get('description', '')}")
    return "\n".join(lines) if lines else "        (none defined)"


def _generate_results_return(results: dict[str, dict]) -> str:
    """Generate the return statement for results."""
    lines = []
    for name, field in results.items():
        lines.append(f'            "{name}": None,  # TODO: Compute {field.get("description", name)}')
    return "\n".join(lines) if lines else '            # TODO: Add result metrics'


def _generate_config_defaults(config: dict[str, dict]) -> str:
    """Generate default config values."""
    lines = []
    for name, field in config.items():
        default = field.get('default') if field.get('default') is not None else field.get('example')
        if default is None:
            field_type = field.get('type', 'TEXT')
            if field_type == "TEXT":
                default = '""'
            elif field_type == "INTEGER":
                default = "0"
            elif field_type == "REAL":
                default = "0.0"
            elif field_type == "BOOLEAN":
                default = "False"
            else:
                default = "None"
        elif isinstance(default, str):
            default = f'"{default}"'
        lines.append(f'        "{name}": {default},')
    return "\n".join(lines) if lines else '        # TODO: Add config parameters'


def _load_template() -> str:
    """Load the experiment template."""
    template_path = Path(__file__).parent.parent / "templates" / "experiment.py.template"
    return template_path.read_text()


def register_scaffold_tools(mcp: FastMCP) -> None:
    """Register scaffold tools with the MCP server."""

    @mcp.tool()
    def scaffold_experiment(name: str, spec: dict[str, Any]) -> ScaffoldResult:
        """Create experiment directory with boilerplate code.

        This creates the full experiment scaffold that follows sciweave patterns.
        Claude Code then fills in the run() method with actual implementation logic.

        Args:
            name: Experiment name (will be converted to snake_case for directory)
            spec: Experiment specification with the following structure:
                - title: str - Human readable title
                - source: str - Path to original proposal
                - motivation: str - Why this experiment matters
                - hypothesis: dict (optional) - With statement, prediction, null_hypothesis, success_criteria
                - config: dict - Config parameters with {name: {type, description, default}}
                - results: dict - Result metrics with {name: {type, description}}
                - dependencies: list[str] (optional) - Python package dependencies
                - implementation_notes: str (optional) - Notes for implementation

        Returns:
            ScaffoldResult with paths to created files.

        Example spec:
            {
                "title": "SAE Feature Geometry Analysis",
                "source": "/path/to/proposal.md",
                "motivation": "Investigate whether SAE features align with task manifolds",
                "hypothesis": {
                    "statement": "20-40% of SAE features will align with manifolds",
                    "prediction": "Aligned features will be more interpretable",
                    "null_hypothesis": "Features are orthogonal to task geometry",
                    "success_criteria": "MI > 0.3 for 20-40% of features"
                },
                "config": {
                    "model_name": {"type": "TEXT", "description": "Model to analyze", "default": "gpt2"},
                    "target_layer": {"type": "INTEGER", "description": "Layer index", "default": 6}
                },
                "results": {
                    "mi_score": {"type": "REAL", "description": "Mutual information score"},
                    "alignment": {"type": "REAL", "description": "Feature-manifold alignment"}
                }
            }
        """
        config = get_config()
        workspace = config.workspace_path

        # Normalize name
        exp_name = _to_snake_case(name)
        exp_dir = workspace / exp_name

        # Create directory structure
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "results").mkdir(exist_ok=True)
        (exp_dir / "configs").mkdir(exist_ok=True)
        (exp_dir / "data").mkdir(exist_ok=True)

        # Extract spec fields
        title = spec.get("title", name)
        source = spec.get("source", "unknown")
        motivation = spec.get("motivation", "")
        hypothesis = spec.get("hypothesis", {})
        spec_config = spec.get("config", {})
        spec_results = spec.get("results", {})
        dependencies = spec.get("dependencies", [])
        impl_notes = spec.get("implementation_notes", "No implementation notes provided")

        # Generate code from template
        template = _load_template()
        class_name = _to_class_name(title)

        hypothesis_statement = hypothesis.get("statement", "N/A") if hypothesis else "N/A"

        code = template.format(
            title=title,
            motivation=motivation,
            hypothesis_statement=hypothesis_statement,
            source=source,
            class_name=class_name,
            config_docstring=_generate_config_docstring(spec_config),
            results_docstring=_generate_results_docstring(spec_results),
            implementation_notes=impl_notes,
            results_return=_generate_results_return(spec_results),
            config_defaults=_generate_config_defaults(spec_config),
            experiment_name=exp_name,
        )

        # Write Python file
        python_file = exp_dir / f"{exp_name}.py"
        python_file.write_text(code, encoding="utf-8")

        # Write spec.yaml
        spec_file = exp_dir / "spec.yaml"
        spec_content = yaml.dump(
            spec,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        spec_file.write_text(spec_content, encoding="utf-8")

        # Create journal.md
        journal_file = exp_dir / "journal.md"
        journal_content = f"""# Experiment Journal: {title}

## Spec Summary
- **Hypothesis:** {hypothesis_statement}
- **Success Criteria:** {hypothesis.get('success_criteria', 'Not specified') if hypothesis else 'Not specified'}

---

"""
        journal_file.write_text(journal_content, encoding="utf-8")

        return ScaffoldResult(
            experiment_path=str(exp_dir),
            python_file=str(python_file),
            spec_file=str(spec_file),
            journal_file=str(journal_file),
            message=f"Created experiment scaffold at {exp_dir}. Implement the run() method in {python_file.name}.",
        )

    @mcp.tool()
    def validate_experiment(name: str) -> ValidationResult:
        """Validate that experiment code follows sciweave patterns.

        Checks:
        - Python file exists and is valid syntax
        - Class subclasses Experiment
        - Has run() method
        - run() returns a dict

        Args:
            name: Experiment name (directory name in workspace)

        Returns:
            ValidationResult with valid flag, errors, and warnings.
        """
        config = get_config()
        workspace = config.workspace_path

        exp_name = _to_snake_case(name)
        exp_dir = workspace / exp_name
        python_file = exp_dir / f"{exp_name}.py"

        errors = []
        warnings = []

        # Check directory exists
        if not exp_dir.exists():
            return ValidationResult(
                valid=False,
                errors=[f"Experiment directory not found: {exp_dir}"],
                warnings=[],
            )

        # Check Python file exists
        if not python_file.exists():
            return ValidationResult(
                valid=False,
                errors=[f"Python file not found: {python_file}"],
                warnings=[],
            )

        # Parse Python file
        try:
            code = python_file.read_text(encoding="utf-8")
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Syntax error in {python_file.name}: {e}"],
                warnings=[],
            )

        # Find class that might subclass Experiment
        experiment_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Experiment":
                        experiment_class = node
                        break

        if experiment_class is None:
            errors.append("No class found that subclasses Experiment")
        else:
            # Check for run method
            has_run = False
            for item in experiment_class.body:
                if isinstance(item, ast.FunctionDef) and item.name == "run":
                    has_run = True
                    # Check if it has a return statement
                    has_return = any(isinstance(n, ast.Return) for n in ast.walk(item))
                    if not has_return:
                        warnings.append("run() method has no return statement")
                    break

            if not has_run:
                errors.append(f"Class {experiment_class.name} has no run() method")

        # Check for spec.yaml
        spec_file = exp_dir / "spec.yaml"
        if not spec_file.exists():
            warnings.append("spec.yaml not found - consider adding for documentation")

        # Check for journal.md
        journal_file = exp_dir / "journal.md"
        if not journal_file.exists():
            warnings.append("journal.md not found - consider adding for tracking")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
