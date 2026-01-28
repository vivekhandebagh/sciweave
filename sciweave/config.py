"""Configuration utilities for SciWeave."""

from typing import Any, Dict
import json


def flatten_config(
    config: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, str]:
    """
    Flatten nested config dict for MLflow params.

    Example:
        {"model": {"lr": 0.01}} -> {"model.lr": "0.01"}

    MLflow params must be strings, so all values are converted.

    Args:
        config: Nested configuration dictionary (or OmegaConf DictConfig)
        parent_key: Prefix for keys (used in recursion)
        sep: Separator between nested keys (default ".")

    Returns:
        Flat dictionary with string values suitable for MLflow params
    """
    items = {}

    # Handle OmegaConf DictConfig by converting to dict
    if hasattr(config, "items") and not isinstance(config, dict):
        config = dict(config)

    for key, value in config.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            items.update(flatten_config(value, new_key, sep))
        elif isinstance(value, (list, tuple)):
            items[new_key] = json.dumps(value)
        else:
            items[new_key] = str(value)

    return items
