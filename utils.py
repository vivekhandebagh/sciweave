import datetime

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
