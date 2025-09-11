#!/usr/bin/env python3
"""
Comprehensive tests for Experiment class
"""

import os
import sys
import sqlite3
import tempfile
import shutil
import time
from abc import ABC, abstractmethod

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_manager import ProjectManager
from experiment import Experiment
import utils


class TestExperiment(Experiment):
    """Test implementation of Experiment"""
    def __init__(self, pm, name, config, mode='dev', should_fail=False):
        super().__init__(pm, name, config, mode)
        self.should_fail = should_fail
    
    def run(self):
        if self.should_fail:
            raise RuntimeError("Experiment failed as requested")
        
        # Simulate work
        time.sleep(0.01)
        
        return {
            'accuracy': 0.95,
            'loss': 0.05,
            'iterations': 100
        }


class TestExperimentClass:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def cleanup(self):
        """Clean up test artifacts"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def setup_test_project(self):
        """Create a test project"""
        os.chdir(self.temp_dir)
        return ProjectManager("test_experiment_project")
    
    def log_result(self, test_name, passed, message=""):
        """Log test results"""
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        if passed:
            self.passed += 1
            print(f"✓ {test_name}")
        else:
            self.failed += 1
            print(f"✗ {test_name}: {message}")
    
    def test_experiment_execution(self):
        """Test basic experiment execution"""
        try:
            pm = self.setup_test_project()
            
            config = {
                'learning_rate': 0.001,
                'batch_size': 32,
                'epochs': 10
            }
            
            exp = TestExperiment(pm, "test_exp", config, mode='dev')
            results = exp()
            
            assert results is not None
            assert 'accuracy' in results
            assert results['accuracy'] == 0.95
            
            # Check database entry
            db_results = pm.query("test_exp", targets='all')
            assert len(db_results) == 1
            assert db_results[0]['run_status'] == 'completed'
            assert db_results[0]['learning_rate'] == 0.001
            assert db_results[0]['accuracy'] == 0.95
            
            self.log_result("Experiment Execution", True)
        except Exception as e:
            self.log_result("Experiment Execution", False, str(e))
    
    def test_experiment_failure_handling(self):
        """Test handling of experiment failures"""
        try:
            pm = self.setup_test_project()
            
            config = {'param': 1}
            exp = TestExperiment(pm, "failing_exp", config, mode='dev', should_fail=True)
            
            try:
                results = exp()
                assert False, "Expected experiment to fail"
            except RuntimeError:
                pass
            
            # Check database shows failure
            db_results = pm.query("failing_exp", targets='all')
            assert len(db_results) == 1
            assert db_results[0]['run_status'] == 'failed'
            
            self.log_result("Failure Handling", True)
        except Exception as e:
            self.log_result("Failure Handling", False, str(e))
    
    def test_multiple_runs(self):
        """Test multiple runs of same experiment"""
        try:
            pm = self.setup_test_project()
            
            config = {'param': 1}
            
            # Run experiment multiple times
            for i in range(3):
                exp = TestExperiment(pm, "multi_run_exp", config, mode='dev')
                exp()
            
            # Check all runs recorded
            db_results = pm.query("multi_run_exp")
            assert len(db_results) == 3
            
            # Check unique run_ids
            run_ids = [r['run_id'] for r in db_results]
            assert len(set(run_ids)) == 3
            
            self.log_result("Multiple Runs", True)
        except Exception as e:
            self.log_result("Multiple Runs", False, str(e))
    
    def test_dev_prod_modes(self):
        """Test dev vs prod mode handling"""
        try:
            pm = self.setup_test_project()
            
            config = {'param': 1}
            
            # Run in dev mode
            exp_dev = TestExperiment(pm, "mode_test", config, mode='dev')
            exp_dev()
            
            # Run in prod mode
            exp_prod = TestExperiment(pm, "mode_test", config, mode='prod')
            exp_prod()
            
            # Check both recorded with correct modes
            db_results = pm.query("mode_test", targets=['run_id', 'mode'])
            assert len(db_results) == 2
            
            modes = [r['mode'] for r in db_results]
            assert 'dev' in modes
            assert 'prod' in modes
            
            self.log_result("Dev/Prod Modes", True)
        except Exception as e:
            self.log_result("Dev/Prod Modes", False, str(e))
    
    def test_config_schema_generation(self):
        """Test automatic schema generation from config"""
        try:
            pm = self.setup_test_project()
            
            config = {
                'str_param': 'test',
                'int_param': 42,
                'float_param': 3.14,
                'bool_param': True
            }
            
            exp = TestExperiment(pm, "schema_test", config)
            exp()
            
            # Check schema was properly created
            schema = pm.get_experiment_schema("schema_test")
            assert schema['str_param'] == 'TEXT'
            assert schema['int_param'] == 'INTEGER'
            assert schema['float_param'] == 'REAL'
            assert schema['bool_param'] == 'BOOLEAN'
            
            self.log_result("Config Schema Generation", True)
        except Exception as e:
            self.log_result("Config Schema Generation", False, str(e))
    
    def test_result_persistence(self):
        """Test that results are properly persisted"""
        try:
            pm = self.setup_test_project()
            
            config = {'param': 1}
            exp = TestExperiment(pm, "persist_test", config)
            original_results = exp()
            
            # Get run_id from database
            db_results = pm.query("persist_test", targets='all')
            run_id = db_results[0]['run_id']
            
            # Create new PM instance and check data persists
            pm2 = ProjectManager("test_experiment_project")
            persisted = pm2.query("persist_test", filters={'run_id': run_id}, targets='all')
            
            assert len(persisted) == 1
            assert persisted[0]['accuracy'] == original_results['accuracy']
            
            self.log_result("Result Persistence", True)
        except Exception as e:
            self.log_result("Result Persistence", False, str(e))
    
    def test_timestamp_generation(self):
        """Test timestamp generation and ordering"""
        try:
            pm = self.setup_test_project()
            
            config = {'param': 1}
            
            # Run experiments with small delays
            for i in range(3):
                exp = TestExperiment(pm, "timestamp_test", config)
                exp()
                time.sleep(0.1)
            
            # Check timestamps are in order
            db_results = pm.query("timestamp_test", targets=['time_stamp'])
            timestamps = [r['time_stamp'] for r in db_results]
            
            # Results should be ordered DESC by default
            for i in range(len(timestamps) - 1):
                assert timestamps[i] > timestamps[i + 1]
            
            self.log_result("Timestamp Generation", True)
        except Exception as e:
            self.log_result("Timestamp Generation", False, str(e))
    
    def test_result_path_handling(self):
        """Test result_path generation"""
        try:
            pm = self.setup_test_project()
            
            # Test default result_path
            config = {'param': 1}
            exp = TestExperiment(pm, "path_test", config)
            exp()
            
            db_results = pm.query("path_test", targets=['result_path'])
            assert len(db_results) == 1
            assert db_results[0]['result_path'].startswith('results/')
            
            self.log_result("Result Path Handling", True)
        except Exception as e:
            self.log_result("Result Path Handling", False, str(e))
    
    def test_empty_results(self):
        """Test handling of experiments that return no results"""
        try:
            pm = self.setup_test_project()
            
            class EmptyExperiment(Experiment):
                def run(self):
                    return {}
            
            config = {'param': 1}
            exp = EmptyExperiment(pm, "empty_test", config)
            exp()
            
            # Check run was recorded even with no results
            db_results = pm.query("empty_test", targets='all')
            assert len(db_results) == 1
            assert db_results[0]['run_status'] == 'completed'
            
            self.log_result("Empty Results Handling", True)
        except Exception as e:
            self.log_result("Empty Results Handling", False, str(e))
    
    def test_database_connection_handling(self):
        """Test database connection management"""
        try:
            pm = self.setup_test_project()
            
            # Create multiple experiments rapidly
            config = {'param': 1}
            for i in range(10):
                exp = TestExperiment(pm, f"conn_test_{i}", config)
                exp()
            
            # All should succeed without connection issues
            for i in range(10):
                results = pm.query(f"conn_test_{i}")
                assert len(results) == 1
            
            self.log_result("Database Connection Handling", True)
        except Exception as e:
            self.log_result("Database Connection Handling", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("Running Experiment Class Tests")
        print("="*60 + "\n")
        
        self.test_experiment_execution()
        self.test_experiment_failure_handling()
        self.test_multiple_runs()
        self.test_dev_prod_modes()
        self.test_config_schema_generation()
        self.test_result_persistence()
        self.test_timestamp_generation()
        self.test_result_path_handling()
        self.test_empty_results()
        self.test_database_connection_handling()
        
        print("\n" + "="*60)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("="*60)
        
        return self.test_results


if __name__ == "__main__":
    tester = TestExperimentClass()
    try:
        results = tester.run_all_tests()
    finally:
        tester.cleanup()