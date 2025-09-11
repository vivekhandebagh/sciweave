import datetime
import json

def flatten_dict(d, parent_key='', sep='_'):
    '''
    Flatten a nested dictionary.
    
    Args:
        d (dict): Dictionary to flatten
        parent_key (str): Key prefix for nested items
        sep (str): Separator between parent and child keys
    
    Returns:
        dict: Flattened dictionary
    '''
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Store lists as JSON strings
            items.append((new_key, json.dumps(v)))
        else:
            items.append((new_key, v))
    return dict(items)

def dict_to_schema(d):
    '''
    Convert a Python dictionary of {key: value} into
    {key: SQL type string}.

    Args:
        d (dict): A dictionary with sample values.

    Returns:
        dict: A dictionary with the same keys but SQL type values.
'''
    type_map = {
        str: "TEXT",
        int: "INTEGER",
        float: "REAL",
        bool: "BOOLEAN",
        bytes: "BLOB",
    }

    sql_dict = {}
    for key, value in d.items():
        if value is None:
            sql_dict[key] = "TEXT"   # fallback if value is None
        else:
            py_type = type(value)
            sql_dict[key] = type_map.get(py_type, "TEXT")  # default TEXT
    return sql_dict


def time_stamp():
    '''Generate ISO format timestamp'''
    return datetime.datetime.now().isoformat()
