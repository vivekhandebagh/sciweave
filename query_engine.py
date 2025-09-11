"""
Query engine for Rex experiments.
Handles all database queries, filtering, and result formatting.
"""

import sqlite3
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import db_utils


# ============================================================================
# Query Building Functions
# ============================================================================

def build_where_clause(filters: Optional[Dict[str, Any]] = None, 
                       time_range: Optional[Union[str, Tuple]] = None) -> Tuple[str, List[Any]]:
    """
    Build a WHERE clause from filters and time range.
    
    Args:
        filters: Dictionary of column:value filters
        time_range: Time filtering - string keyword or tuple (start, end)
        
    Returns:
        Tuple of (where_sql, values_list)
    """
    where_clauses = []
    values = []
    
    # Process time range filters
    if time_range:
        time_clause, time_values = build_time_filter(time_range)
        if time_clause:
            where_clauses.append(time_clause)
            values.extend(time_values)
    
    # Process regular column filters
    if filters:
        for col, val in filters.items():
            if isinstance(val, str) and val.startswith('>'):
                # Handle comparison operators
                where_clauses.append(f"{col} > ?")
                values.append(float(val[1:]) if '.' in val else int(val[1:]))
            elif isinstance(val, str) and val.startswith('<'):
                where_clauses.append(f"{col} < ?")
                values.append(float(val[1:]) if '.' in val else int(val[1:]))
            elif isinstance(val, str) and val.startswith('!='):
                where_clauses.append(f"{col} != ?")
                values.append(val[2:])
            elif isinstance(val, str) and '%' in val:
                # Handle LIKE patterns
                where_clauses.append(f"{col} LIKE ?")
                values.append(val)
            elif isinstance(val, list):
                # Handle IN clause
                placeholders = ','.join(['?' for _ in val])
                where_clauses.append(f"{col} IN ({placeholders})")
                values.extend(val)
            else:
                # Standard equality
                where_clauses.append(f"{col} = ?")
                values.append(val)
    
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return where_sql, values


def build_time_filter(time_range: Union[str, Tuple]) -> Tuple[str, List[str]]:
    """
    Build time filter clause.
    
    Args:
        time_range: String keyword or tuple (start, end)
        
    Returns:
        Tuple of (where_clause, values)
    """
    if isinstance(time_range, str):
        # Handle keyword time ranges
        now = datetime.now()
        
        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            return "time_stamp >= ? AND time_stamp <= ?", [start, end]
            
        elif time_range == "yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            return "time_stamp >= ? AND time_stamp <= ?", [start, end]
            
        elif time_range == "week":
            week_ago = now - timedelta(days=7).isoformat()
            return "time_stamp >= ?", [week_ago]
            
        elif time_range == "month":
            month_ago = now - timedelta(days=30).isoformat()
            return "time_stamp >= ?", [month_ago]
            
        elif time_range == "last_n_days":
            # Parse "last_7_days" format
            parts = time_range.split('_')
            if len(parts) == 3 and parts[0] == "last" and parts[2] == "days":
                n_days = int(parts[1])
                n_days_ago = (now - timedelta(days=n_days)).isoformat()
                return "time_stamp >= ?", [n_days_ago]
        
        else:
            raise ValueError(f"Unknown time range keyword: {time_range}")
            
    elif isinstance(time_range, tuple) and len(time_range) == 2:
        # Handle tuple (start, end) time ranges
        start, end = time_range
        clauses = []
        values = []
        
        if start is not None:
            clauses.append("time_stamp >= ?")
            values.append(start)
        if end is not None:
            clauses.append("time_stamp <= ?")
            values.append(end)
            
        return " AND ".join(clauses), values
    
    else:
        raise ValueError("time_range must be a keyword string or tuple (start, end)")


def build_select_clause(targets: Optional[Union[str, List[str]]], 
                       table_name: str,
                       conn: sqlite3.Connection,
                       required_schema: Optional[Dict[str, str]] = None,
                       config_schema: Optional[Dict[str, str]] = None) -> str:
    """
    Build SELECT clause based on target specification.
    
    Args:
        targets: What to select - None, 'all', 'results', or list of columns
        table_name: Name of the table to query
        conn: Database connection
        required_schema: Required columns (for 'results' mode)
        config_schema: Config columns (for 'results' mode)
        
    Returns:
        SELECT clause string
    """
    if targets is None:
        # Return only run_ids
        return "run_id"
        
    elif targets == 'all':
        # Return all columns
        return "*"
        
    elif targets == 'results':
        # Return run_id + result columns (exclude required and config)
        cursor = conn.cursor()
        quoted_table = db_utils.quote_identifier(table_name)
        cursor.execute(f"PRAGMA table_info({quoted_table})")
        all_cols = [row[1] for row in cursor.fetchall()]
        
        # Determine which columns are results
        required_cols = set(required_schema.keys()) if required_schema else set()
        config_cols = set(config_schema.keys()) if config_schema else set()
        
        result_cols = [col for col in all_cols 
                      if col not in required_cols and col not in config_cols]
        result_cols.insert(0, 'run_id')  # Always include run_id
        
        return ', '.join(result_cols)
        
    else:
        # Specific columns requested
        if isinstance(targets, str):
            targets = [targets]
            
        # Validate columns exist
        cursor = conn.cursor()
        quoted_table = db_utils.quote_identifier(table_name)
        cursor.execute(f"PRAGMA table_info({quoted_table})")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        invalid_targets = [col for col in targets if col not in existing_cols]
        if invalid_targets:
            raise ValueError(f"Invalid target columns not in table: {invalid_targets}")
            
        return ', '.join(targets)


# ============================================================================
# Query Execution Functions
# ============================================================================

def execute_query(conn: sqlite3.Connection, 
                 table_name: str,
                 filters: Optional[Dict[str, Any]] = None,
                 targets: Optional[Union[str, List[str]]] = None,
                 time_range: Optional[Union[str, Tuple]] = None,
                 order_by: str = "time_stamp DESC",
                 limit: Optional[int] = None,
                 required_schema: Optional[Dict[str, str]] = None,
                 config_schema: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Execute a query on an experiment table.
    
    Args:
        conn: Database connection
        table_name: Table to query
        filters: Column filters
        targets: What columns to return
        time_range: Time filtering
        order_by: ORDER BY clause
        limit: LIMIT clause
        required_schema: Required columns (for 'results' mode)
        config_schema: Config columns (for 'results' mode)
        
    Returns:
        List of result dictionaries
    """
    cursor = conn.cursor()
    
    # Build query components
    select_clause = build_select_clause(targets, table_name, conn, 
                                       required_schema, config_schema)
    where_clause, values = build_where_clause(filters, time_range)
    
    # Build full query
    quoted_table = db_utils.quote_identifier(table_name)
    query = f"SELECT {select_clause} FROM {quoted_table}{where_clause}"
    
    if order_by:
        query += f" ORDER BY {order_by}"
    
    if limit:
        query += f" LIMIT {limit}"
    
    # Execute query
    cursor.execute(query, values)
    rows = cursor.fetchall()
    
    # Convert to list of dicts
    if rows:
        column_names = [description[0] for description in cursor.description]
        results = [dict(zip(column_names, row)) for row in rows]
    else:
        results = []
    
    return results


def query_by_tag(conn: sqlite3.Connection,
                 table_name: str,
                 tag: str) -> List[Dict[str, Any]]:
    """
    Query runs that have a specific tag.
    
    Args:
        conn: Database connection
        table_name: Table to query
        tag: Tag to search for
        
    Returns:
        List of matching runs
    """
    cursor = conn.cursor()
    quoted_table = db_utils.quote_identifier(table_name)
    
    # Tags are comma-separated, so we need multiple LIKE conditions
    query = f"""
        SELECT * FROM {quoted_table}
        WHERE tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags = ?
        ORDER BY time_stamp DESC
    """
    
    # Handle different positions of tag in comma-separated list
    params = (
        f'%,{tag},%',  # Tag in middle
        f'{tag},%',    # Tag at start
        f'%,{tag}',    # Tag at end
        tag            # Only tag
    )
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if rows:
        column_names = [description[0] for description in cursor.description]
        results = [dict(zip(column_names, row)) for row in rows]
    else:
        results = []
    
    return results


# ============================================================================
# Summary and Aggregation Functions
# ============================================================================

def get_experiment_summary(conn: sqlite3.Connection,
                          table_name: str,
                          experiment_name: str) -> Dict[str, Any]:
    """
    Get summary statistics for an experiment.
    
    Args:
        conn: Database connection
        table_name: Table name
        experiment_name: Experiment name for display
        
    Returns:
        Dictionary with summary statistics
    """
    cursor = conn.cursor()
    quoted_table = db_utils.quote_identifier(table_name)
    
    # Get run count by status
    cursor.execute(f"""
        SELECT run_status, COUNT(*) as count 
        FROM {quoted_table}
        GROUP BY run_status
    """)
    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get total runs
    cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
    total_runs = cursor.fetchone()[0]
    
    # Get latest run
    cursor.execute(f"""
        SELECT run_id, time_stamp, run_status 
        FROM {quoted_table}
        ORDER BY time_stamp DESC 
        LIMIT 1
    """)
    latest_run = cursor.fetchone()
    
    # Get date range
    cursor.execute(f"""
        SELECT MIN(time_stamp), MAX(time_stamp)
        FROM {quoted_table}
    """)
    date_range = cursor.fetchone()
    
    summary = {
        'experiment_name': experiment_name,
        'table_name': table_name,
        'total_runs': total_runs,
        'status_counts': status_counts,
        'date_range': {
            'first_run': date_range[0] if date_range else None,
            'last_run': date_range[1] if date_range else None
        }
    }
    
    if latest_run:
        summary['latest_run'] = {
            'run_id': latest_run[0],
            'time_stamp': latest_run[1],
            'status': latest_run[2]
        }
    else:
        summary['latest_run'] = None
    
    return summary


def get_aggregate_stats(conn: sqlite3.Connection,
                        table_name: str,
                        metric_columns: List[str],
                        group_by: Optional[str] = None,
                        filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get aggregate statistics for numeric columns.
    
    Args:
        conn: Database connection
        table_name: Table to query
        metric_columns: Columns to aggregate
        group_by: Optional column to group by
        filters: Optional filters
        
    Returns:
        Dictionary of aggregate statistics
    """
    cursor = conn.cursor()
    quoted_table = db_utils.quote_identifier(table_name)
    
    # Build WHERE clause if filters provided
    where_clause, values = build_where_clause(filters)
    
    stats = {}
    
    for col in metric_columns:
        # Build aggregation query
        query = f"""
            SELECT 
                AVG({col}) as avg,
                MIN({col}) as min,
                MAX({col}) as max,
                COUNT({col}) as count
        """
        
        if group_by:
            query += f", {group_by}"
        
        query += f" FROM {quoted_table}{where_clause}"
        
        if group_by:
            query += f" GROUP BY {group_by}"
        
        cursor.execute(query, values)
        
        if group_by:
            # Return grouped results
            stats[col] = {}
            for row in cursor.fetchall():
                group_val = row[-1]  # Last column is the group_by value
                stats[col][group_val] = {
                    'avg': row[0],
                    'min': row[1],
                    'max': row[2],
                    'count': row[3]
                }
        else:
            # Return single result
            row = cursor.fetchone()
            if row:
                stats[col] = {
                    'avg': row[0],
                    'min': row[1],
                    'max': row[2],
                    'count': row[3]
                }
    
    return stats


# ============================================================================
# Cross-Experiment Query Functions
# ============================================================================

def cross_experiment_query(conn: sqlite3.Connection,
                          experiment_tables: List[Tuple[str, str]],
                          filters: Optional[Dict[str, Any]] = None,
                          targets: Optional[List[str]] = None,
                          time_range: Optional[Union[str, Tuple]] = None) -> List[Dict[str, Any]]:
    """
    Query across multiple experiments.
    
    Args:
        conn: Database connection
        experiment_tables: List of (experiment_name, table_name) tuples
        filters: Filters to apply to all experiments
        targets: Columns to return
        time_range: Time filtering
        
    Returns:
        Combined results from all experiments
    """
    all_results = []
    
    for exp_name, table_name in experiment_tables:
        # Add experiment_name to each result
        results = execute_query(
            conn, table_name, filters, targets, time_range
        )
        
        # Add experiment name to each row
        for row in results:
            row['_experiment'] = exp_name
        
        all_results.extend(results)
    
    # Sort by timestamp if available
    if all_results and 'time_stamp' in all_results[0]:
        all_results.sort(key=lambda x: x['time_stamp'], reverse=True)
    
    return all_results


def compare_experiments(conn: sqlite3.Connection,
                        experiment_tables: List[Tuple[str, str]],
                        metric_columns: List[str]) -> Dict[str, Any]:
    """
    Compare metrics across experiments.
    
    Args:
        conn: Database connection
        experiment_tables: List of (experiment_name, table_name) tuples
        metric_columns: Columns to compare
        
    Returns:
        Comparison statistics
    """
    comparison = {}
    
    for exp_name, table_name in experiment_tables:
        stats = get_aggregate_stats(conn, table_name, metric_columns)
        comparison[exp_name] = stats
    
    return comparison


# ============================================================================
# Best Run Selection Functions
# ============================================================================

def get_best_runs(conn: sqlite3.Connection,
                 table_name: str,
                 metric: str,
                 n: int = 5,
                 mode: str = 'max',
                 filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get the best N runs based on a metric.
    
    Args:
        conn: Database connection
        table_name: Table to query
        metric: Column to optimize
        n: Number of runs to return
        mode: 'max' for highest values, 'min' for lowest
        filters: Optional filters
        
    Returns:
        List of best runs
    """
    order = "DESC" if mode == 'max' else "ASC"
    
    return execute_query(
        conn, table_name,
        filters=filters,
        targets='all',
        order_by=f"{metric} {order}",
        limit=n
    )


# ============================================================================
# Helper Functions
# ============================================================================

def format_results_for_display(results: List[Dict[str, Any]], 
                               columns: Optional[List[str]] = None,
                               max_width: int = 100) -> str:
    """
    Format query results for display.
    
    Args:
        results: Query results
        columns: Columns to display (None for all)
        max_width: Maximum column width
        
    Returns:
        Formatted string for display
    """
    if not results:
        return "No results found"
    
    # Determine columns to display
    if columns:
        display_cols = columns
    else:
        display_cols = list(results[0].keys())
    
    # Calculate column widths
    widths = {}
    for col in display_cols:
        max_len = len(col)
        for row in results:
            val_len = len(str(row.get(col, '')))
            max_len = max(max_len, min(val_len, max_width))
        widths[col] = max_len
    
    # Build header
    header = " | ".join(col.ljust(widths[col]) for col in display_cols)
    separator = "-|-".join("-" * widths[col] for col in display_cols)
    
    # Build rows
    rows = []
    for result in results:
        row = " | ".join(
            str(result.get(col, '')).ljust(widths[col])[:widths[col]]
            for col in display_cols
        )
        rows.append(row)
    
    return "\n".join([header, separator] + rows)