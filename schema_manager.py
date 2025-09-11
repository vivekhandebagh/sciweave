"""
Schema management utilities for Rex experiments.
Handles schema inference, evolution, and config-to-database interface.
"""

import json
from typing import Dict, Any, List, Tuple, Optional

# ============================================================================
# Config Processing Functions
# ============================================================================

def process_config(config: Any) -> Dict[str, Any]:
    """
    Process any config type (dict, DictConfig) into a flat dictionary suitable for database.
    
    Args:
        config: Dictionary, DictConfig, or nested structure
        
    Returns:
        Flat dictionary with database-compatible values
    """
    # Check if it's a DictConfig (from Hydra/OmegaConf)
    if hasattr(config, '__class__') and config.__class__.__name__ == 'DictConfig':
        # Convert to regular dict - OmegaConf must be available if user is passing DictConfig
        from omegaconf import OmegaConf
        config = OmegaConf.to_container(config, resolve=True)
    
    # Ensure we have a dict at this point
    if not isinstance(config, dict):
        raise TypeError(f"Config must be a dictionary or DictConfig, got {type(config)}")
    
    # Flatten if nested
    if is_nested(config):
        return flatten_dict(config)
    
    return config


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """
    Flatten a nested dictionary into a single-level dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Prefix for nested keys
        sep: Separator between parent and child keys
        
    Returns:
        Flattened dictionary with concatenated keys
        
    Example:
        {'model': {'lr': 0.01}} -> {'model_lr': 0.01}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Store lists as JSON strings for SQL compatibility
            items.append((new_key, json.dumps(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: Dict[str, Any], sep: str = '_') -> Dict[str, Any]:
    """
    Unflatten a dictionary back to nested structure.
    
    Args:
        d: Flattened dictionary
        sep: Separator used in flattening
        
    Returns:
        Nested dictionary
        
    Example:
        {'model_lr': 0.01} -> {'model': {'lr': 0.01}}
    """
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Try to parse JSON strings back to lists
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        
        current[parts[-1]] = value
    return result


def is_nested(d: Dict[str, Any]) -> bool:
    """Check if a dictionary contains nested dictionaries."""
    return any(isinstance(v, dict) for v in d.values())


# ============================================================================
# Schema Inference Functions
# ============================================================================

def infer_schema(d: Dict[str, Any]) -> Dict[str, str]:
    """
    Infer SQL schema from a Python dictionary.
    
    Args:
        d: Dictionary with sample values
        
    Returns:
        Dictionary mapping keys to SQL type strings
    """
    type_map = {
        str: "TEXT",
        int: "INTEGER", 
        float: "REAL",
        bool: "BOOLEAN",
        bytes: "BLOB",
    }
    
    schema = {}
    for key, value in d.items():
        if value is None:
            schema[key] = "TEXT"  # Default for None
        else:
            py_type = type(value)
            schema[key] = type_map.get(py_type, "TEXT")  # Default to TEXT
    
    return schema


def merge_schemas(base_schema: Dict[str, str], new_schema: Dict[str, str]) -> Dict[str, str]:
    """
    Merge two schemas, preferring new schema for conflicts.
    
    Args:
        base_schema: Existing schema
        new_schema: New schema to merge
        
    Returns:
        Merged schema
    """
    merged = base_schema.copy()
    merged.update(new_schema)
    return merged


# ============================================================================
# Schema Evolution Functions
# ============================================================================

def detect_schema_changes(old_schema: Dict[str, str], 
                         new_schema: Dict[str, str]) -> Dict[str, Any]:
    """
    Detect changes between two schemas.
    
    Args:
        old_schema: Previous schema
        new_schema: New schema
        
    Returns:
        Dictionary describing changes:
        - added: List of new columns
        - removed: List of removed columns  
        - type_changes: List of (column, old_type, new_type) tuples
    """
    old_keys = set(old_schema.keys())
    new_keys = set(new_schema.keys())
    
    changes = {
        'added': list(new_keys - old_keys),
        'removed': list(old_keys - new_keys),
        'type_changes': []
    }
    
    # Check for type changes in common columns
    common_keys = old_keys & new_keys
    for key in common_keys:
        if old_schema[key] != new_schema[key]:
            changes['type_changes'].append({
                'column': key,
                'old_type': old_schema[key],
                'new_type': new_schema[key]
            })
    
    return changes


def can_evolve_schema(changes: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if schema changes can be applied safely.
    
    Args:
        changes: Dictionary of schema changes from detect_schema_changes
        
    Returns:
        Tuple of (can_evolve, list_of_issues)
    """
    issues = []
    
    # Adding columns is always safe
    # Removing columns is not safe (would lose data)
    if changes['removed']:
        issues.append(f"Cannot remove columns: {changes['removed']}")
    
    # Type changes are problematic in SQLite
    for change in changes['type_changes']:
        # Some type changes are safe
        if not is_safe_type_change(change['old_type'], change['new_type']):
            issues.append(
                f"Unsafe type change for {change['column']}: "
                f"{change['old_type']} -> {change['new_type']}"
            )
    
    return len(issues) == 0, issues


def is_safe_type_change(old_type: str, new_type: str) -> bool:
    """
    Check if a type change is safe for SQLite.
    
    Args:
        old_type: Current SQL type
        new_type: Desired SQL type
        
    Returns:
        True if the type change is safe
    """
    # SQLite is flexible with types, but some changes are problematic
    safe_changes = {
        ('INTEGER', 'REAL'),  # Int to float is safe
        ('INTEGER', 'TEXT'),  # Int to text is safe
        ('REAL', 'TEXT'),     # Float to text is safe
        ('BOOLEAN', 'INTEGER'),  # Bool to int is safe
        ('BOOLEAN', 'TEXT'),  # Bool to text is safe
    }
    
    return (old_type, new_type) in safe_changes


# ============================================================================
# Schema Validation Functions
# ============================================================================

def validate_schema(schema: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate a schema for compatibility.
    
    Args:
        schema: Schema dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    valid_types = {'TEXT', 'INTEGER', 'REAL', 'BOOLEAN', 'BLOB'}
    
    for column, sql_type in schema.items():
        # Check column name
        if not is_valid_column_name(column):
            errors.append(f"Invalid column name: {column}")
        
        # Check SQL type
        if sql_type not in valid_types:
            errors.append(f"Invalid SQL type for {column}: {sql_type}")
    
    return len(errors) == 0, errors


def is_valid_column_name(name: str) -> bool:
    """
    Check if a column name is valid for SQL.
    
    Args:
        name: Column name to validate
        
    Returns:
        True if valid
    """
    import re
    # Column names should start with letter, contain only alphanumeric and underscore
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name))


def sanitize_column_name(name: str) -> str:
    """
    Sanitize a column name for SQL compatibility.
    
    Args:
        name: Column name to sanitize
        
    Returns:
        Sanitized column name
    """
    import re
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'col_' + sanitized
    
    return sanitized


# ============================================================================
# Config/Schema Compatibility Functions
# ============================================================================

def make_config_schema_compatible(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a config dictionary to be schema-compatible.
    
    Args:
        config: Config dictionary that may have incompatible values
        
    Returns:
        Config with all values made SQL-compatible
    """
    compatible = {}
    
    for key, value in config.items():
        # Sanitize key
        safe_key = sanitize_column_name(key)
        
        # Convert value to SQL-compatible type
        if isinstance(value, (list, tuple)):
            compatible[safe_key] = json.dumps(value)
        elif isinstance(value, dict):
            compatible[safe_key] = json.dumps(value)
        elif value is None:
            compatible[safe_key] = None
        else:
            compatible[safe_key] = value
    
    return compatible


def prepare_config_for_storage(config: Any) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Prepare any config for database storage.
    
    Args:
        config: Raw config (dict, DictConfig, nested, etc.)
        
    Returns:
        Tuple of (processed_config, schema)
    """
    # Process config into flat dict
    processed = process_config(config)
    
    # Make it schema-compatible
    compatible = make_config_schema_compatible(processed)
    
    # Infer schema
    schema = infer_schema(compatible)
    
    return compatible, schema


# ============================================================================
# Schema Comparison Functions
# ============================================================================

def schemas_compatible(schema1: Dict[str, str], schema2: Dict[str, str]) -> bool:
    """
    Check if two schemas are compatible (can coexist in same table).
    
    Args:
        schema1: First schema
        schema2: Second schema
        
    Returns:
        True if schemas are compatible
    """
    # Check overlapping columns have same types
    common_keys = set(schema1.keys()) & set(schema2.keys())
    
    for key in common_keys:
        if schema1[key] != schema2[key]:
            # Check if it's a safe type difference
            if not is_safe_type_change(schema1[key], schema2[key]):
                return False
    
    return True


def get_required_schema() -> Dict[str, str]:
    """
    Get the required base schema for all experiments.
    
    Returns:
        Dictionary of required columns and their types
    """
    return {
        'run_id': 'TEXT',
        'time_stamp': 'TEXT',
        'experiment_name': 'TEXT',
        'mode': 'TEXT',
        'run_status': 'TEXT',
        'result_path': 'TEXT',
        'tags': 'TEXT',
        'notes': 'TEXT'
    }


def extend_with_required_schema(schema: Dict[str, str]) -> Dict[str, str]:
    """
    Extend a schema with required fields.
    
    Args:
        schema: User-provided schema
        
    Returns:
        Schema with required fields added
    """
    required = get_required_schema()
    full_schema = required.copy()
    full_schema.update(schema)
    return full_schema