"""SciWeave MCP Server - MLflow experiment access for AI agents."""

import os
import logging
from typing import Optional

import mlflow
from mlflow.tracking import MlflowClient
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (required for stdio transport)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("sciweave-mcp")


def get_client() -> MlflowClient:
    """Get MLflow client with configured tracking URI."""
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "databricks")
    mlflow.set_tracking_uri(tracking_uri)
    return MlflowClient()


@mcp.tool()
def list_experiments(prefix: Optional[str] = None) -> str:
    """
    List all MLflow experiments.

    Args:
        prefix: Optional prefix to filter experiments (e.g., "my-project/")
    """
    client = get_client()
    experiments = client.search_experiments()

    results = []
    for exp in experiments:
        if prefix and not exp.name.startswith(prefix):
            continue
        results.append(f"- {exp.name} (id: {exp.experiment_id})")

    if not results:
        return "No experiments found."

    return "Experiments:\n" + "\n".join(results)


@mcp.tool()
def search_runs(
    experiment_name: str,
    filter_string: Optional[str] = None,
    max_results: int = 10,
    order_by: str = "start_time DESC"
) -> str:
    """
    Search runs in an experiment.

    Args:
        experiment_name: Full experiment name (e.g., "my-project/transformer_v1")
        filter_string: MLflow filter (e.g., "metrics.accuracy > 0.9")
        max_results: Maximum number of runs to return
        order_by: Sort order (e.g., "metrics.accuracy DESC")
    """
    client = get_client()
    experiment = client.get_experiment_by_name(experiment_name)

    if not experiment:
        return f"Experiment '{experiment_name}' not found."

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=filter_string or "",
        max_results=max_results,
        order_by=[order_by] if order_by else None
    )

    if not runs:
        return "No runs found."

    results = []
    for run in runs:
        info = run.info
        metrics = run.data.metrics
        params = run.data.params

        # Format key metrics
        metric_strs = [f"{k}={v:.4f}" for k, v in list(metrics.items())[:5]]
        param_strs = [f"{k}={v}" for k, v in list(params.items())[:3]]

        results.append(
            f"Run: {info.run_id[:8]}\n"
            f"  Status: {info.status}\n"
            f"  Metrics: {', '.join(metric_strs) or 'none'}\n"
            f"  Params: {', '.join(param_strs) or 'none'}"
        )

    return "\n\n".join(results)


def _format_run_details(run) -> str:
    """Format a run's complete details for output."""
    info = run.info
    metrics = run.data.metrics
    params = run.data.params
    tags = run.data.tags

    lines = [
        f"Run ID: {info.run_id}",
        f"Experiment ID: {info.experiment_id}",
        f"Status: {info.status}",
        f"Start Time: {info.start_time}",
        f"End Time: {info.end_time}",
        f"Artifact URI: {info.artifact_uri}",
    ]

    # ALL parameters (no truncation)
    lines.append("")
    lines.append("=" * 40)
    lines.append("PARAMETERS")
    lines.append("=" * 40)
    if params:
        for k, v in sorted(params.items()):
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  (none)")

    # ALL metrics (no truncation) - these are the results
    lines.append("")
    lines.append("=" * 40)
    lines.append("METRICS (Results)")
    lines.append("=" * 40)
    if metrics:
        for k, v in sorted(metrics.items()):
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  (none)")

    # ALL user tags (filter out mlflow.* system tags)
    lines.append("")
    lines.append("=" * 40)
    lines.append("TAGS")
    lines.append("=" * 40)
    user_tags = {k: v for k, v in tags.items() if not k.startswith("mlflow.")}
    if user_tags:
        for k, v in sorted(user_tags.items()):
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


@mcp.tool()
def get_run(run_id: str) -> str:
    """
    Get COMPLETE information about a specific run including all parameters,
    metrics (results), and tags.

    Args:
        run_id: The MLflow run ID (full or first 8 characters)

    Returns:
        Full run details with all parameters, metrics, and tags
    """
    client = get_client()

    # Handle short run IDs by searching
    if len(run_id) < 32:
        runs = client.search_runs(
            experiment_ids=[],
            filter_string=f"run_id LIKE '{run_id}%'",
            max_results=1
        )
        if not runs:
            return f"Run '{run_id}' not found."
        run = runs[0]
    else:
        run = client.get_run(run_id)

    return _format_run_details(run)


@mcp.tool()
def get_latest_run(experiment_name: str) -> str:
    """
    Get the most recent run's COMPLETE details from an experiment.

    This is the primary tool for AI agents to check results after running
    an experiment. Returns all parameters, metrics (results), and tags.

    Args:
        experiment_name: Full experiment name (e.g., "my-project/transformer_v1")

    Returns:
        Full details of the most recent run
    """
    client = get_client()
    experiment = client.get_experiment_by_name(experiment_name)

    if not experiment:
        return f"Experiment '{experiment_name}' not found."

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=1
    )

    if not runs:
        return f"No runs found in experiment '{experiment_name}'."

    return _format_run_details(runs[0])


@mcp.tool()
def get_metric_history(run_id: str, metric_name: str) -> str:
    """
    Get the history of a metric across training steps.

    Args:
        run_id: The MLflow run ID
        metric_name: Name of the metric (e.g., "loss", "accuracy")
    """
    client = get_client()

    try:
        history = client.get_metric_history(run_id, metric_name)
    except Exception as e:
        return f"Error fetching metric history: {e}"

    if not history:
        return f"No history found for metric '{metric_name}'."

    # Format as table
    lines = [f"Metric: {metric_name}", "Step\tValue"]
    for point in history:
        lines.append(f"{point.step}\t{point.value:.6f}")

    return "\n".join(lines)


@mcp.tool()
def get_best_run(
    experiment_name: str,
    metric: str,
    mode: str = "max"
) -> str:
    """
    Find the best run in an experiment by a metric.

    Args:
        experiment_name: Full experiment name
        metric: Metric to optimize (e.g., "accuracy", "loss")
        mode: "max" for highest value, "min" for lowest
    """
    order = "DESC" if mode == "max" else "ASC"
    return search_runs(
        experiment_name=experiment_name,
        order_by=f"metrics.{metric} {order}",
        max_results=1
    )


@mcp.tool()
def compare_runs(run_ids: str) -> str:
    """
    Compare multiple runs side by side.

    Args:
        run_ids: Comma-separated run IDs to compare
    """
    client = get_client()
    ids = [r.strip() for r in run_ids.split(",")]

    runs_data = []
    all_metrics = set()
    all_params = set()

    for rid in ids:
        try:
            run = client.get_run(rid)
            runs_data.append({
                "id": rid[:8],
                "metrics": run.data.metrics,
                "params": run.data.params
            })
            all_metrics.update(run.data.metrics.keys())
            all_params.update(run.data.params.keys())
        except Exception as e:
            runs_data.append({"id": rid[:8], "error": str(e)})

    # Build comparison table
    lines = ["Run Comparison:", ""]

    # Header
    header = "Metric/Param\t" + "\t".join(r["id"] for r in runs_data)
    lines.append(header)
    lines.append("-" * len(header))

    # Metrics
    for metric in sorted(all_metrics):
        row = [metric]
        for run in runs_data:
            if "error" in run:
                row.append("ERR")
            elif metric in run["metrics"]:
                row.append(f"{run['metrics'][metric]:.4f}")
            else:
                row.append("-")
        lines.append("\t".join(row))

    lines.append("")

    # Params (show only differing ones)
    for param in sorted(all_params):
        values = [r.get("params", {}).get(param, "-") for r in runs_data]
        if len(set(values)) > 1:  # Only show if values differ
            row = [param] + values
            lines.append("\t".join(row))

    return "\n".join(lines)


@mcp.tool()
def list_artifacts(run_id: str, path: str = "") -> str:
    """
    List artifacts for a run.

    Args:
        run_id: The MLflow run ID
        path: Optional path within artifacts directory
    """
    client = get_client()

    try:
        artifacts = client.list_artifacts(run_id, path)
    except Exception as e:
        return f"Error listing artifacts: {e}"

    if not artifacts:
        return "No artifacts found."

    lines = ["Artifacts:"]
    for artifact in artifacts:
        size = f" ({artifact.file_size} bytes)" if artifact.file_size else ""
        lines.append(f"  {artifact.path}{size}")

    return "\n".join(lines)


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
