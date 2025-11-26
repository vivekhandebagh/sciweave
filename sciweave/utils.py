import datetime

def time_stamp():
    '''Generate ISO format timestamp'''
    return datetime.datetime.now().isoformat()

# Legacy imports for backward compatibility
# TODO: Update all usages to import from schema_manager directly
from .schema_manager import flatten_dict, infer_schema as dict_to_schema
