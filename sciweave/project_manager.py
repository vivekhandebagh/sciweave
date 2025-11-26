import sqlite3
from abc import ABC, abstractmethod
import datetime
import uuid
import json
from . import utils
from . import db_utils
from . import query_engine as qe
from . import schema_manager as sm

PROJECT_NAME = ""


class ProjectManager:
    """
    Manages experiment registry and database coordination for a project.
    
    This is the main entry point for users to interact with Rex.
    All database operations should go through ProjectManager.
    """
    
    # ========================================================================
    # INITIALIZATION & SETUP
    # ========================================================================
    
    def __init__(self, project_name: str):
        """Initialize project manager with database and registry setup"""
        # Set default required schema for all experiments
        self.REQUIRED_SCHEMA = {
            'run_id': 'TEXT',           # Unique identifier for each run
            'time_stamp': 'TEXT',       # ISO timestamp of run
            'experiment_name': 'TEXT',  # Name of the experiment
            'mode': 'TEXT',             # dev/prod mode
            'run_status': 'TEXT',       # started/running/completed/failed
            'result_path': 'TEXT',      # Path to result files
            'tags': 'TEXT',             # Comma-separated tags
            'notes': 'TEXT'             # Run-specific notes/description
        }
    
        self.project_name = project_name
        self.db_path = f"{project_name}.db"
        self._experiment_registry = {}
        
        # Ensure registry table exists and load existing experiments
        self._ensure_registry_table()
        self._load_registry()
    
    def _ensure_registry_table(self):
        """Create project registry table to track all experiments"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS _experiment_registry (
                experiment_id TEXT PRIMARY KEY,
                experiment_name TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                created_timestamp TEXT NOT NULL,
                last_modified TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_registry(self):
        """Load existing experiment registry from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT experiment_id, experiment_name, schema_json, created_timestamp, last_modified, description 
            FROM _experiment_registry
        ''')
        
        for row in cursor.fetchall():
            experiment_id, experiment_name, schema_json, created_ts, modified_ts, description = row
            # Key by experiment_name for easier access
            self._experiment_registry[experiment_name] = {
                'experiment_id': experiment_id,  # Store id as a field
                'schema': json.loads(schema_json),
                'created_timestamp': created_ts,
                'last_modified': modified_ts,
                'description': description or ""
            }
        
        conn.close()
    
    # ========================================================================
    # INTERNAL HELPER METHODS (Private)
    # ========================================================================
    
    def _generate_experiment_id(self):
        """Generate a unique experiment ID using UUID"""
        short_uuid = str(uuid.uuid4())[:8]
        return f"exp_{short_uuid}"
    
    def _create_experiment_table(self, experiment_id: str, schema: dict):
        """Create new experiment table with given schema"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Validate and sanitize the schema
        validated_schema = db_utils.validate_schema(schema)
        
        # Build CREATE TABLE SQL with proper quoting
        columns = []
        for field, data_type in validated_schema.items():
            quoted_field = db_utils.quote_identifier(field)
            if field == 'run_id':
                columns.append(f"{quoted_field} TEXT PRIMARY KEY")
            else:
                columns.append(f"{quoted_field} {data_type}")
        
        columns_sql = ", ".join(columns)
        quoted_table = db_utils.quote_identifier(experiment_id)
        create_sql = f"CREATE TABLE IF NOT EXISTS {quoted_table} ({columns_sql})"
        cursor.execute(create_sql)
        
        conn.commit()
        conn.close()
    
    def _register_experiment(self, experiment_id: str, experiment_name: str, schema: dict, description: str = ""):
        """Register experiment in the project registry"""
        
        # Update in-memory registry - keyed by experiment_name
        self._experiment_registry[experiment_name] = {
            'experiment_id': experiment_id,  # Store id as a field
            'schema': schema,
            'created_timestamp': utils.time_stamp(),
            'last_modified': utils.time_stamp(),
            'description': description
        }
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO _experiment_registry 
            (experiment_id, experiment_name, schema_json, created_timestamp, last_modified, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            experiment_id,
            experiment_name,
            json.dumps(schema),
            utils.time_stamp(),
            utils.time_stamp(),
            description
        ))
        
        conn.commit()
        conn.close()

    # ========================================================================
    # EXPERIMENT LIFECYCLE MANAGEMENT
    # ========================================================================
    
    def init_experiment(self, experiment_name: str, experiment_schema: dict):
        """Initialize experiment - creates table if needed and returns experiment_id"""
        
        # Validate experiment name
        try:
            db_utils.sanitize_identifier(experiment_name)
        except ValueError as e:
            raise ValueError(f"Invalid experiment name: {e}")
        
        # Look for existing experiment by name
        if self.experiment_exists(experiment_name):
            # Return existing experiment's table
            experiment_id = self._experiment_registry[experiment_name]['experiment_id']
            print(f"Using existing experiment table: {experiment_id}")
            return experiment_id
        else:
            # Create new experiment
            experiment_id = self._generate_experiment_id()
            
            # Combine required schema with experiment-specific schema
            full_schema = self.REQUIRED_SCHEMA.copy()
            full_schema.update(experiment_schema)
            
            self._create_experiment_table(experiment_id, full_schema)
            self._register_experiment(experiment_id, experiment_name, full_schema)
            
            print(f"Created and registered new experiment table: {experiment_id}")
            return experiment_id

    # ========================================================================
    # EXPERIMENT INFORMATION & DISCOVERY
    # ========================================================================

    def get_experiment_id(self, experiment_name: str):
        """Get the table name (experiment_id) for a given experiment"""
        if not self.experiment_exists(experiment_name):
            return None
        return self._experiment_registry[experiment_name]['experiment_id']
    
    def get_experiment_schema(self, experiment_name: str):
        """Get schema for specific experiment"""
        return self._experiment_registry.get(experiment_name, {}).get('schema', {})
    
    def list_experiments(self):
        """List all experiments registered in this project"""
        return list(self._experiment_registry.keys())  # Now returns experiment names directly
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        ''', (table_name,))
        
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
        
    # ========================================================================
    # DATABASE UTILITIES
    # ========================================================================
    
    def get_connection(self):
        """Get database connection for this project"""
        return sqlite3.connect(self.db_path)
    
    # ========================================================================
    # QUERY OPERATIONS (Delegates to query_engine)
    # ========================================================================
    
    def query(self, experiment_name: str, filters: dict = None, targets=None, time_range=None):
        '''
        Query experiment runs with filters and return specified columns.
        
        Args:
            experiment_name: Name of the experiment to query
            filters: Dict of {column: value} to filter runs
            time_range: Time filtering - can be:
                - Tuple (start, end) where start/end are ISO timestamps or None
                - String keywords: "today", "yesterday", "week", "month"
                - None for no time filtering
            targets: What to return - None (run_ids only), 'all' (all columns), 
                    'results' (run_id + result columns), or list of column names
        
        Returns:
            List of dicts with requested data
        '''
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        schema = self._experiment_registry[experiment_name]['schema']
        
        # Validate filter columns exist in schema
        if filters:
            invalid_cols = [col for col in filters.keys() if col not in schema]
            if invalid_cols:
                raise ValueError(f"Invalid filter columns not in schema: {invalid_cols}")
        
        # Use query engine to execute the query
        conn = self.get_connection()
        try:
            results = qe.execute_query(
                conn=conn,
                table_name=experiment_id,
                filters=filters,
                targets=targets,
                time_range=time_range,
                required_schema=self.REQUIRED_SCHEMA,
                config_schema=None  # TODO: Pass actual config schema if needed
            )
        finally:
            conn.close()
        
        return results

    def experiment_exists(self, experiment_name: str) -> bool:
        """Check if an experiment exists in the registry"""
        return experiment_name in self._experiment_registry
    
    def get_experiment_info(self, experiment_name: str):
        """Get all registry info for an experiment"""
        return self._experiment_registry.get(experiment_name)
    
    # ========================================================================
    # EXPERIMENT RENAMING & REFACTORING
    # ========================================================================
    
    def rename_experiment(self, old_name: str, new_name: str):
        """Rename an experiment while preserving its ID and data"""
        if old_name not in self._experiment_registry:
            raise ValueError(f"Experiment '{old_name}' not found")
        if new_name in self._experiment_registry:
            raise ValueError(f"Experiment '{new_name}' already exists")
        
        # Get the experiment data
        exp_data = self._experiment_registry[old_name]
        experiment_id = exp_data['experiment_id']
        
        # Update in-memory registry
        self._experiment_registry[new_name] = exp_data
        del self._experiment_registry[old_name]
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE _experiment_registry 
            SET experiment_name = ?, last_modified = ?
            WHERE experiment_id = ?
        ''', (new_name, utils.time_stamp(), experiment_id))
        conn.commit()
        conn.close()
    
    def refactor_experiment_name(self, current_name: str, new_name: str):
        '''
        Rename an experiment, updating both the registry and all run records.
        
        Args:
            current_name: Current name of the experiment
            new_name: New name for the experiment
        '''
        # Check if current experiment exists
        if current_name not in self._experiment_registry:
            raise ValueError(f"Experiment '{current_name}' not found")
        
        # Check if new name is already taken
        if new_name in self._experiment_registry:
            raise ValueError(f"Experiment '{new_name}' already exists")
        
        # Get the experiment data and ID
        exp_data = self._experiment_registry[current_name].copy()
        experiment_id = exp_data['experiment_id']
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Step 1: Update the experiment_name column in all runs
            cursor.execute(f"""
                UPDATE {experiment_id} 
                SET experiment_name = ?
                WHERE experiment_name = ?
            """, (new_name, current_name))
            
            # Step 2: Update the registry table
            cursor.execute('''
                UPDATE _experiment_registry 
                SET experiment_name = ?, last_modified = ?
                WHERE experiment_id = ?
            ''', (new_name, utils.time_stamp(), experiment_id))
            
            # Step 3: Update in-memory registry
            self._experiment_registry[new_name] = exp_data
            del self._experiment_registry[current_name]
            
            conn.commit()
            print(f"Successfully renamed experiment '{current_name}' to '{new_name}'")
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            raise RuntimeError(f"Failed to rename experiment: {str(e)}")
        finally:
            conn.close()
    
    # ========================================================================
    # METADATA MANAGEMENT (Tags, Notes, Custom Columns)
    # ========================================================================
    
    def add_tags(self, experiment_name: str, run_id: str, tags: list, append: bool = False):
        """Update tags for a specific run
        
        Args:
            experiment_name: Name of the experiment
            run_id: ID of the run to update
            tags: List of tags to set/append
            append: If True, append to existing tags; if False, replace
        """
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if append:
            # Get existing tags
            cursor.execute(f"SELECT tags FROM {experiment_id} WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row and row[0]:
                existing_tags = row[0].split(',')
                tags = list(set(existing_tags + tags))  # Combine and deduplicate
        
        tags_str = ','.join(tags) if tags else ''
        cursor.execute(f"UPDATE {experiment_id} SET tags = ? WHERE run_id = ?", (tags_str, run_id))
        conn.commit()
        conn.close()
    
    def add_notes(self, experiment_name: str, run_id: str, notes: str):
        """Update notes for a specific run"""
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {experiment_id} SET notes = ? WHERE run_id = ?", (notes, run_id))
        conn.commit()
        conn.close()
    
    def get_runs_by_tag(self, experiment_name: str, tag: str):
        """Get all runs with a specific tag"""
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        
        # Use query engine for tag search
        conn = self.get_connection()
        try:
            results = qe.query_by_tag(conn, experiment_id, tag)
        finally:
            conn.close()
        
        return results
    
    def add_custom_column(self, experiment_name: str, column_name: str, column_type: str = 'TEXT'):
        """Add a custom column to an experiment table
        
        Args:
            experiment_name: Name of the experiment
            column_name: Name of the new column
            column_type: SQL type for the column (TEXT, INTEGER, REAL, etc.)
        """
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        
        # Validate column name using schema_manager
        if not sm.is_valid_column_name(column_name):
            column_name = sm.sanitize_column_name(column_name)
            print(f"Column name sanitized to: {column_name}")
        
        # Validate the new schema
        new_schema = {column_name: column_type}
        is_valid, errors = sm.validate_schema(new_schema)
        if not is_valid:
            raise ValueError(f"Invalid schema: {errors}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            quoted_table = db_utils.quote_identifier(experiment_id)
            quoted_column = db_utils.quote_identifier(column_name)
            cursor.execute(f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {column_type}")
            
            # Update schema in registry
            self._experiment_registry[experiment_name]['schema'][column_name] = column_type
            
            # Update registry in database
            cursor.execute('''
                UPDATE _experiment_registry 
                SET schema_json = ?, last_modified = ?
                WHERE experiment_id = ?
            ''', (
                json.dumps(self._experiment_registry[experiment_name]['schema']),
                utils.time_stamp(),
                experiment_id
            ))
            
            conn.commit()
            print(f"Added column '{column_name}' to experiment '{experiment_name}'")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column '{column_name}' already exists")
            else:
                raise
        finally:
            conn.close()
    
    # ========================================================================
    # SUMMARY & STATISTICS
    # ========================================================================
    
    def get_experiment_summary(self, experiment_name: str):
        """Get summary statistics for an experiment"""
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        
        # Use query engine for summary
        conn = self.get_connection()
        try:
            summary = qe.get_experiment_summary(conn, experiment_id, experiment_name)
        finally:
            conn.close()
        
        return summary

    def get_best_runs(self, experiment_name: str, metric: str, n: int = 5, mode: str = 'max'):
        """Get the best N runs based on a metric"""
        if not self.experiment_exists(experiment_name):
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment_id = self._experiment_registry[experiment_name]['experiment_id']
        
        conn = self.get_connection()
        try:
            results = qe.get_best_runs(conn, experiment_id, metric, n, mode)
        finally:
            conn.close()
        
        return results