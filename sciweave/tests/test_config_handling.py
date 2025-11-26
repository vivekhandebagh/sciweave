#!/usr/bin/env python3
"""
Test config handling without requiring Hydra
"""

import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_manager import ProjectManager
from experiment import Experiment
import schema_manager as sm


class TestExperiment(Experiment):
    """Simple test experiment"""
    def run(self):
        return {"accuracy": 0.95}


def test_plain_dict():
    """Test with regular Python dict"""
    print("\nTesting plain dictionary...")
    
    config = {
        "learning_rate": 0.01,
        "batch_size": 32,
        "epochs": 10
    }
    
    # Test schema_manager processing
    processed = sm.process_config(config)
    assert processed == config
    print("✓ Plain dict processed correctly")
    
    return True


def test_nested_dict():
    """Test with nested dictionary"""
    print("\nTesting nested dictionary...")
    
    config = {
        "model": {
            "learning_rate": 0.01,
            "layers": [64, 32]
        },
        "training": {
            "batch_size": 32,
            "epochs": 10
        }
    }
    
    # Test schema_manager processing
    processed = sm.process_config(config)
    
    # Should be flattened
    assert "model_learning_rate" in processed
    assert "training_batch_size" in processed
    assert processed["model_layers"] == '[64, 32]'  # Lists become JSON strings
    
    print(f"✓ Nested dict flattened correctly: {processed}")
    
    return True


def test_with_experiment():
    """Test config handling in actual experiment"""
    print("\nTesting with Experiment class...")
    
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    
    try:
        pm = ProjectManager("test_configs")
        
        # Test 1: Simple config
        simple_config = {"lr": 0.01, "batch": 32}
        exp1 = TestExperiment(pm, "simple", simple_config)
        exp1()
        print("✓ Simple config experiment worked")
        
        # Test 2: Nested config
        nested_config = {
            "optimizer": {"lr": 0.001, "momentum": 0.9},
            "model": {"hidden_size": 128}
        }
        exp2 = TestExperiment(pm, "nested", nested_config)
        exp2()
        print("✓ Nested config experiment worked")
        
        return True
        
    except Exception as e:
        print(f"✗ Experiment test failed: {e}")
        return False
    finally:
        os.chdir("..")
        shutil.rmtree(temp_dir)


def test_invalid_config():
    """Test that invalid configs are rejected"""
    print("\nTesting invalid configs...")
    
    # Test non-dict config
    try:
        sm.process_config("not a dict")
        print("✗ Should have rejected string config")
        return False
    except TypeError as e:
        print(f"✓ Correctly rejected non-dict: {e}")
    
    try:
        sm.process_config(123)
        print("✗ Should have rejected numeric config")
        return False
    except TypeError as e:
        print(f"✓ Correctly rejected number: {e}")
    
    return True


if __name__ == "__main__":
    print("="*60)
    print("Testing Config Handling (No Hydra Required)")
    print("="*60)
    
    results = []
    results.append(test_plain_dict())
    results.append(test_nested_dict())
    results.append(test_with_experiment())
    results.append(test_invalid_config())
    
    print("\n" + "="*60)
    if all(results):
        print("✓ All config tests passed!")
    else:
        print("✗ Some tests failed")