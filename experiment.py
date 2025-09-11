import sqlite3
from abc import ABC, abstractmethod
import datetime
import uuid
import json
import utils
import db_utils
import schema_manager as sm
from project_manager import ProjectManager

class Experiment(ABC):

    def __init__(self, pm: ProjectManager, experiment_name: str, config, mode: str='dev', result_path: str=None):
        
        
        self.pm = pm
        self.conn = self.pm.get_connection()
        self.cursor = self.conn.cursor()
        self.experiment_name = experiment_name
        self.mode = mode # mode must be either 'dev' or 'prod'
        
        # Store original config for use in run() method
        self.original_config = config
        
        # Process config through schema manager
        self.config, self.experiment_schema = sm.prepare_config_for_storage(config)

        # set default result_path to results/timestamp/
        self.result_path = result_path

        # This returns the experiment_id
        self.experiment_id = pm.init_experiment(self.experiment_name, self.experiment_schema)

    def _generate_run_id(self):
        '''Needs to automatically generate a unique run id.'''
        short_uuid = str(uuid.uuid4())[:8]
        return f"run_{short_uuid}"

    def _update_table(self, phase: str, data: dict = None):
        """Update experiment table in three phases:
        1. pre_experiment: Insert row with required schema and run_status='started'
        2. pre_results: Update row with config parameters and run_status='running' 
        3. post_results: Update row with results and run_status='completed'/'failed'
        """
        if phase == 'pre_experiment':
            # Insert initial row with required schema
            required_data = {
                'run_id': data['run_id'],
                'time_stamp': data['time_stamp'], 
                'experiment_name': self.experiment_name,
                'mode': self.mode,
                'run_status': 'started',
                'result_path': data.get('result_path', '')
            }
            
            columns = ', '.join(required_data.keys())
            placeholders = ', '.join(['?' for _ in required_data])
            values = list(required_data.values())
            
            sql = f"INSERT INTO {self.experiment_id} ({columns}) VALUES ({placeholders})"
            self.cursor.execute(sql, values)
            self.conn.commit()
            
        elif phase == 'pre_results':
            # Update with config parameters
            if data:
                set_clauses = []
                values = []
                for key, value in data.items():
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
                
                # Update run_status
                set_clauses.append("run_status = ?")
                values.append('running')
                values.append(data['run_id'])  # for WHERE clause
                
                sql = f"UPDATE {self.experiment_id} SET {', '.join(set_clauses)} WHERE run_id = ?"
                self.cursor.execute(sql, values)
                self.conn.commit()
                
        elif phase == 'post_results':
            # Update with results
            if data:
                set_clauses = []
                values = []
                for key, value in data.items():
                    if key != 'run_id':  # Don't update run_id
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                # Update run_status based on success
                run_status = data.get('run_status', 'completed')
                set_clauses.append("run_status = ?")
                values.append(run_status)
                values.append(data['run_id'])  # for WHERE clause
                
                sql = f"UPDATE {self.experiment_id} SET {', '.join(set_clauses)} WHERE run_id = ?"
                self.cursor.execute(sql, values)
                self.conn.commit()

    def _prerun_updates(self):
        '''
        Before we call self.run(), we need to generate run id and timestamp. the experiment name is already given. 
        mode is also given. run status should default to 'started' then later modified to 'interrupted,' 'failed', or 'completed'
        result path will remain null by default.
        this completes the required schema

        then we need to take the values of config and store it since the experiment schema will be your config anyways.
        '''
        
        run_id = self._generate_run_id()
        time_stamp = utils.time_stamp()

        if self.result_path is None:
            self.result_path = f'results/{time_stamp}'
        
        # Combine required data and config data into single INSERT
        all_data = {
            'run_id': run_id,
            'time_stamp': time_stamp, 
            'experiment_name': self.experiment_name,
            'mode': self.mode,
            'run_status': 'started',
            'result_path': self.result_path,
            'tags': '',  # Initialize empty
            'notes': ''  # Initialize empty
        }
        
        # Add config values
        all_data.update(self.config)
        
        columns = ', '.join(all_data.keys())
        placeholders = ', '.join(['?' for _ in all_data])
        values = list(all_data.values())
        
        # Use quoted table name for safety
        quoted_table = db_utils.quote_identifier(self.experiment_id)
        sql = f"INSERT INTO {quoted_table} ({columns}) VALUES ({placeholders})"
        self.cursor.execute(sql, values)
        self.conn.commit()
        
        return run_id  # Return run_id for use in postrun_updates
        
    def _postrun_updates(self, run_id, results, status='completed'):
        '''
        Update the existing row with results and final status.
        Dynamically adds columns if they don't exist.
        
        Args:
            run_id: The run_id of the row to update
            results: Dictionary of results from self.run()
            status: Final status ('completed', 'failed', 'interrupted')
        '''
        try:
            if not results:
                # Just update the status if no results
                quoted_table = db_utils.quote_identifier(self.experiment_id)
                sql = f"UPDATE {quoted_table} SET run_status = ? WHERE run_id = ?"
                self.cursor.execute(sql, (status, run_id))
                self.conn.commit()
                return
            
            # First ensure all result columns exist
            result_schema = sm.infer_schema(results)
            db_utils.ensure_columns_exist(self.conn, self.experiment_id, result_schema)
            
            # Build UPDATE statement for results
            set_clauses = []
            values = []
            
            # Add each result field with proper quoting
            for key, value in results.items():
                sanitized_key = db_utils.sanitize_identifier(key)
                quoted_key = db_utils.quote_identifier(sanitized_key)
                set_clauses.append(f"{quoted_key} = ?")
                values.append(value)
            
            # Add final status
            set_clauses.append('"run_status" = ?')
            values.append(status)
            
            # Add run_id for WHERE clause
            values.append(run_id)
            
            # Execute UPDATE with quoted table name
            quoted_table = db_utils.quote_identifier(self.experiment_id)
            sql = f"UPDATE {quoted_table} SET {', '.join(set_clauses)} WHERE run_id = ?"
            self.cursor.execute(sql, values)
            self.conn.commit()
            
        except Exception as e:
            # If update fails, try to save to backup
            print(f"Failed to update results: {e}")
            backup_data = {
                'run_id': run_id,
                'status': status,
                'results': results,
                'experiment_id': self.experiment_id,
                'error': str(e)
            }
            db_utils.create_backup_json(backup_data)
            raise

    @db_utils.retry_on_lock(max_retries=3)
    def __call__(self, *args, **kwds):
        """Handle all the boilerplate code for experiment execution with error recovery"""
        
        run_id = None
        try:
            # Pre-run updates: insert row with required fields and config
            run_id = self._prerun_updates()
            
            # Run the experiment
            results = self.run()
            
            # Post-run updates: update row with results and status
            try:
                self._postrun_updates(run_id, results, status='completed')
            except Exception as update_error:
                # If post-update fails, still return results (they're backed up)
                print(f"Warning: Failed to save results to database: {update_error}")
                print("Results have been backed up to JSON file")
                # Don't re-raise - experiment succeeded, just DB write failed
            
            return results
            
        except Exception as e:
            # Handle experiment failure
            if run_id:
                try:
                    self._postrun_updates(run_id, None, status='failed')
                except Exception as update_error:
                    print(f"Warning: Failed to update failure status: {update_error}")
            
            # Always re-raise the original experiment exception
            raise e

    @abstractmethod
    def run(self):
        # must return a dict containing the results that need to get stored in the database
        pass
