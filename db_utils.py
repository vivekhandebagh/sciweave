"""
Database utility functions for safe SQL operations
"""

import re
import sqlite3
import time
import functools
from typing import Any, Dict, List, Optional


# SQL reserved keywords to avoid in identifiers
SQL_KEYWORDS = {
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE', 'JOIN', 'ON',
    'CREATE', 'DROP', 'ALTER', 'TABLE', 'INDEX', 'VIEW', 'TRIGGER',
    'AND', 'OR', 'NOT', 'NULL', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES',
    'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL'
}


def sanitize_identifier(name: str, max_length: int = 64) -> str:
    """
    Sanitize a database identifier (table/column name) for safe SQL usage.
    
    Args:
        name: The identifier to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized identifier
        
    Raises:
        ValueError: If the identifier is invalid or dangerous
    """
    if not name:
        raise ValueError("Identifier cannot be empty")
    
    # Check length
    if len(name) > max_length:
        raise ValueError(f"Identifier '{name}' exceeds maximum length of {max_length}")
    
    # Check if it's a reserved keyword
    if name.upper() in SQL_KEYWORDS:
        raise ValueError(f"'{name}' is a reserved SQL keyword")
    
    # Only allow alphanumeric, underscore, and dash (but not at start)
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_\-]*$', name):
        raise ValueError(
            f"Invalid identifier '{name}'. Must start with a letter and contain "
            "only letters, numbers, underscores, and dashes"
        )
    
    # Replace dashes with underscores for SQL compatibility
    sanitized = name.replace('-', '_')
    
    return sanitized


def quote_identifier(name: str) -> str:
    """
    Properly quote a SQL identifier to prevent injection.
    
    Args:
        name: The identifier to quote
        
    Returns:
        Quoted identifier safe for SQL
    """
    # First sanitize
    sanitized = sanitize_identifier(name)
    
    # Then quote it (using double quotes for SQLite)
    # Escape any existing quotes
    escaped = sanitized.replace('"', '""')
    
    return f'"{escaped}"'


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> Dict[str, str]:
    """
    Get all columns and their types for a table.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        Dictionary mapping column names to SQL types
    """
    cursor = conn.cursor()
    
    # Use parameterized query for safety
    sanitized_table = sanitize_identifier(table_name)
    cursor.execute(f"PRAGMA table_info({quote_identifier(sanitized_table)})")
    
    columns = {}
    for row in cursor.fetchall():
        col_name = row[1]
        col_type = row[2]
        columns[col_name] = col_type
    
    return columns


def ensure_columns_exist(conn: sqlite3.Connection, table_name: str, 
                        required_columns: Dict[str, str]) -> List[str]:
    """
    Ensure all required columns exist in a table, adding missing ones.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        required_columns: Dictionary of column names to SQL types
        
    Returns:
        List of columns that were added
    """
    existing_columns = get_table_columns(conn, table_name)
    added_columns = []
    
    cursor = conn.cursor()
    sanitized_table = sanitize_identifier(table_name)
    quoted_table = quote_identifier(sanitized_table)
    
    for col_name, col_type in required_columns.items():
        if col_name not in existing_columns:
            # Add the missing column
            sanitized_col = sanitize_identifier(col_name)
            quoted_col = quote_identifier(sanitized_col)
            
            # Use safe SQL with proper quoting
            alter_sql = f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_col} {col_type}"
            
            try:
                cursor.execute(alter_sql)
                added_columns.append(col_name)
                print(f"Added column '{col_name}' to table '{table_name}'")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
    
    if added_columns:
        conn.commit()
    
    return added_columns


def retry_on_lock(max_retries: int = 3, initial_delay: float = 0.1):
    """
    Decorator to retry database operations on lock errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (doubles each time)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower():
                        last_exception = e
                        if attempt < max_retries - 1:
                            print(f"Database locked, retrying in {delay}s...")
                            time.sleep(delay)
                            delay *= 2  # Exponential backoff
                        continue
                    raise
                except Exception:
                    raise
            
            # All retries failed
            raise RuntimeError(
                f"Operation failed after {max_retries} retries: {last_exception}"
            )
        
        return wrapper
    return decorator


def validate_schema(schema: Dict[str, str]) -> Dict[str, str]:
    """
    Validate and sanitize a schema dictionary.
    
    Args:
        schema: Dictionary mapping column names to SQL types
        
    Returns:
        Validated and sanitized schema
        
    Raises:
        ValueError: If schema contains invalid identifiers
    """
    valid_types = {'TEXT', 'INTEGER', 'REAL', 'BOOLEAN', 'BLOB'}
    validated = {}
    
    for col_name, col_type in schema.items():
        # Sanitize column name
        sanitized_name = sanitize_identifier(col_name)
        
        # Validate type (convert to string first in case it's not)
        col_type_str = str(col_type)
        col_type_upper = col_type_str.upper()
        if col_type_upper not in valid_types:
            # Default to TEXT for unknown types
            col_type_upper = 'TEXT'
        
        validated[sanitized_name] = col_type_upper
    
    return validated


def create_backup_json(data: dict, backup_path: str = None) -> str:
    """
    Create a JSON backup of data that failed to save to database.
    
    Args:
        data: Data to backup
        backup_path: Optional path for backup file
        
    Returns:
        Path to the backup file
    """
    import json
    import os
    from datetime import datetime
    
    if backup_path is None:
        os.makedirs("backups", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/failed_save_{timestamp}.json"
    
    with open(backup_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"Data backed up to {backup_path}")
    return backup_path