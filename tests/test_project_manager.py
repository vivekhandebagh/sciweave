#!/usr/bin/env python3
"""
Comprehensive tests for ProjectManager class
"""

import os
import sys
import sqlite3
import json
import tempfile
import shutil
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_manager import ProjectManager
import utils


class TestProjectManager:
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
        return ProjectManager("test_project")
    
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
    
    def test_project_creation(self):
        """Test basic project creation"""
        try:
            pm = self.setup_test_project()
            assert os.path.exists("test_project.db")
            
            # Check registry table exists
            conn = sqlite3.connect("test_project.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_experiment_registry'")
            assert cursor.fetchone() is not None
            conn.close()
            
            self.log_result("Project Creation", True)
        except Exception as e:
            self.log_result("Project Creation", False, str(e))
    
    def test_experiment_creation(self):
        """Test experiment creation and registration"""
        try:
            pm = self.setup_test_project()
            
            # Create experiment with schema
            schema = {'learning_rate': 0.001, 'batch_size': 32}
            exp_id = pm.init_experiment("test_exp", utils.dict_to_schema(schema))
            
            assert exp_id is not None
            assert pm.experiment_exists("test_exp")
            assert "test_exp" in pm.list_experiments()
            
            self.log_result("Experiment Creation", True)
        except Exception as e:
            self.log_result("Experiment Creation", False, str(e))
    
    def test_duplicate_experiment_handling(self):
        """Test handling of duplicate experiments"""
        try:
            pm = self.setup_test_project()
            
            schema = {'param1': 1}
            exp_id1 = pm.init_experiment("test_exp", utils.dict_to_schema(schema))
            exp_id2 = pm.init_experiment("test_exp", utils.dict_to_schema(schema))
            
            # Should reuse the same experiment
            assert exp_id1 == exp_id2
            
            self.log_result("Duplicate Experiment Handling", True)
        except Exception as e:
            self.log_result("Duplicate Experiment Handling", False, str(e))
    
    def test_query_functionality(self):
        """Test query with various filters"""
        try:
            pm = self.setup_test_project()
            
            # Create experiment and add test data
            schema = {'accuracy': 0.95, 'loss': 0.05}
            exp_id = pm.init_experiment("test_exp", utils.dict_to_schema(schema))
            
            # Insert test runs
            conn = pm.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            
            test_runs = [
                ('run_001', now.isoformat(), 'test_exp', 'prod', 'completed', '', 'best,paper', 'Best run', 0.95, 0.05),
                ('run_002', yesterday.isoformat(), 'test_exp', 'dev', 'completed', '', 'baseline', 'Baseline', 0.85, 0.15),
                ('run_003', week_ago.isoformat(), 'test_exp', 'dev', 'failed', '', '', '', 0.75, 0.25),
            ]
            
            for run in test_runs:
                cursor.execute(f"""
                    INSERT INTO {exp_id} 
                    (run_id, time_stamp, experiment_name, mode, run_status, result_path, tags, notes, accuracy, loss)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, run)
            conn.commit()
            conn.close()
            
            # Test different query types
            
            # 1. Query today's runs
            results = pm.query("test_exp", time_range="today")
            assert len(results) == 1
            
            # 2. Query with filters
            results = pm.query("test_exp", filters={'mode': 'prod'})
            assert len(results) == 1
            
            # 3. Query with specific targets
            results = pm.query("test_exp", targets=['run_id', 'accuracy', 'loss'])
            assert len(results) == 3
            assert 'accuracy' in results[0]
            
            # 4. Query with time range tuple
            results = pm.query("test_exp", time_range=(yesterday.isoformat(), now.isoformat()))
            assert len(results) == 2
            
            self.log_result("Query Functionality", True)
        except Exception as e:
            self.log_result("Query Functionality", False, str(e))
    
    def test_tag_management(self):
        """Test tag addition and querying"""
        try:
            pm = self.setup_test_project()
            
            schema = {'param1': 1}
            exp_id = pm.init_experiment("test_exp", utils.dict_to_schema(schema))
            
            # Add a test run
            conn = pm.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {exp_id} 
                (run_id, time_stamp, experiment_name, mode, run_status, result_path, tags, notes, param1)
                VALUES ('run_001', ?, 'test_exp', 'dev', 'completed', '', '', '', 1)
            """, (utils.time_stamp(),))
            conn.commit()
            conn.close()
            
            # Test tag operations
            pm.add_tags("test_exp", "run_001", ["best", "paper"])
            
            # Get runs by tag
            results = pm.get_runs_by_tag("test_exp", "best")
            assert len(results) == 1
            assert "best" in results[0]['tags']
            
            # Test append
            pm.add_tags("test_exp", "run_001", ["v1.0"], append=True)
            results = pm.get_runs_by_tag("test_exp", "v1.0")
            assert len(results) == 1
            
            self.log_result("Tag Management", True)
        except Exception as e:
            self.log_result("Tag Management", False, str(e))
    
    def test_experiment_renaming(self):
        """Test experiment renaming functionality"""
        try:
            pm = self.setup_test_project()
            
            schema = {'param1': 1}
            exp_id = pm.init_experiment("old_name", utils.dict_to_schema(schema))
            
            # Add test data
            conn = pm.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {exp_id} 
                (run_id, time_stamp, experiment_name, mode, run_status, result_path, tags, notes, param1)
                VALUES ('run_001', ?, 'old_name', 'dev', 'completed', '', '', '', 1)
            """, (utils.time_stamp(),))
            conn.commit()
            conn.close()
            
            # Test rename
            pm.refactor_experiment_name("old_name", "new_name")
            
            assert not pm.experiment_exists("old_name")
            assert pm.experiment_exists("new_name")
            
            # Check data was updated
            results = pm.query("new_name", targets='all')
            assert len(results) == 1
            assert results[0]['experiment_name'] == 'new_name'
            
            self.log_result("Experiment Renaming", True)
        except Exception as e:
            self.log_result("Experiment Renaming", False, str(e))
    
    def test_custom_columns(self):
        """Test adding custom columns"""
        try:
            pm = self.setup_test_project()
            
            schema = {'param1': 1}
            pm.init_experiment("test_exp", utils.dict_to_schema(schema))
            
            # Add custom column
            pm.add_custom_column("test_exp", "gpu_hours", "REAL")
            
            # Check schema updated
            schema = pm.get_experiment_schema("test_exp")
            assert 'gpu_hours' in schema
            
            # Try adding duplicate
            pm.add_custom_column("test_exp", "gpu_hours", "REAL")  # Should not error
            
            self.log_result("Custom Columns", True)
        except Exception as e:
            self.log_result("Custom Columns", False, str(e))
    
    def test_error_handling(self):
        """Test error handling for invalid operations"""
        try:
            pm = self.setup_test_project()
            errors_caught = []
            
            # 1. Query non-existent experiment
            try:
                pm.query("non_existent")
            except ValueError as e:
                errors_caught.append("query_nonexistent")
            
            # 2. Rename non-existent experiment
            try:
                pm.refactor_experiment_name("non_existent", "new_name")
            except ValueError as e:
                errors_caught.append("rename_nonexistent")
            
            # 3. Add tags to non-existent experiment
            try:
                pm.add_tags("non_existent", "run_001", ["tag"])
            except ValueError as e:
                errors_caught.append("tags_nonexistent")
            
            # 4. Rename to existing name
            pm.init_experiment("exp1", {})
            pm.init_experiment("exp2", {})
            try:
                pm.refactor_experiment_name("exp1", "exp2")
            except ValueError as e:
                errors_caught.append("rename_duplicate")
            
            assert len(errors_caught) == 4
            self.log_result("Error Handling", True)
        except Exception as e:
            self.log_result("Error Handling", False, str(e))
    
    def test_special_characters(self):
        """Test handling of special characters in names"""
        try:
            pm = self.setup_test_project()
            
            # Test with special characters
            special_names = [
                "exp-with-dashes",
                "exp_with_underscores",
                "exp.with.dots",
                "exp123numbers"
            ]
            
            for name in special_names:
                pm.init_experiment(name, {'param': 1})
                assert pm.experiment_exists(name)
            
            self.log_result("Special Characters", True)
        except Exception as e:
            self.log_result("Special Characters", False, str(e))
    
    def test_large_scale_operations(self):
        """Test performance with many experiments and runs"""
        try:
            pm = self.setup_test_project()
            
            # Create multiple experiments
            for i in range(10):
                pm.init_experiment(f"exp_{i}", {'param': i})
            
            # Add many runs to one experiment
            exp_id = pm.get_experiment_id("exp_0")
            conn = pm.get_connection()
            cursor = conn.cursor()
            
            for i in range(100):
                cursor.execute(f"""
                    INSERT INTO {exp_id}
                    (run_id, time_stamp, experiment_name, mode, run_status, result_path, tags, notes, param)
                    VALUES (?, ?, 'exp_0', 'dev', 'completed', '', '', '', ?)
                """, (f"run_{i:04d}", utils.time_stamp(), i))
            
            conn.commit()
            conn.close()
            
            # Test query performance
            results = pm.query("exp_0")
            assert len(results) == 100
            
            self.log_result("Large Scale Operations", True)
        except Exception as e:
            self.log_result("Large Scale Operations", False, str(e))
    
    def test_concurrent_access(self):
        """Test concurrent database access"""
        try:
            pm1 = self.setup_test_project()
            pm2 = ProjectManager("test_project")  # Second instance
            
            # Both should see the same experiments
            pm1.init_experiment("shared_exp", {'param': 1})
            assert pm2.experiment_exists("shared_exp")
            
            self.log_result("Concurrent Access", True)
        except Exception as e:
            self.log_result("Concurrent Access", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("Running ProjectManager Tests")
        print("="*60 + "\n")
        
        self.test_project_creation()
        self.test_experiment_creation()
        self.test_duplicate_experiment_handling()
        self.test_query_functionality()
        self.test_tag_management()
        self.test_experiment_renaming()
        self.test_custom_columns()
        self.test_error_handling()
        self.test_special_characters()
        self.test_large_scale_operations()
        self.test_concurrent_access()
        
        print("\n" + "="*60)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("="*60)
        
        return self.test_results


if __name__ == "__main__":
    tester = TestProjectManager()
    try:
        results = tester.run_all_tests()
    finally:
        tester.cleanup()