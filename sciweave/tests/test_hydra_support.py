#!/usr/bin/env python3
"""
Test Hydra DictConfig support in Experiment class
"""

import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_manager import ProjectManager
from experiment import Experiment

# Try to import OmegaConf
try:
    from omegaconf import DictConfig, OmegaConf
    HYDRA_AVAILABLE = True
except ImportError:
    HYDRA_AVAILABLE = False
    print("Hydra/OmegaConf not installed - skipping DictConfig tests")


class TestExperiment(Experiment):
    """Simple test experiment"""
    def run(self):
        return {"accuracy": 0.95}


def test_plain_dict():
    """Test with regular Python dict"""
    print("\nTesting with plain dictionary...")
    
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    
    try:
        pm = ProjectManager("test_dict")
        
        # Plain dictionary config
        config = {
            "learning_rate": 0.01,
            "batch_size": 32,
            "epochs": 10
        }
        
        exp = TestExperiment(pm, "dict_exp", config)
        results = exp()
        
        print(f"✓ Plain dict config worked")
        print(f"  Config type: {type(exp.config)}")
        print(f"  Config: {exp.config}")
        return True
        
    except Exception as e:
        print(f"✗ Plain dict test failed: {e}")
        return False
    finally:
        os.chdir("..")
        shutil.rmtree(temp_dir)


def test_dict_config():
    """Test with Hydra DictConfig"""
    if not HYDRA_AVAILABLE:
        print("\nSkipping DictConfig test - OmegaConf not available")
        return True
    
    print("\nTesting with DictConfig...")
    
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    
    try:
        pm = ProjectManager("test_dictconfig")
        
        # Create a DictConfig
        config_dict = {
            "model": {
                "learning_rate": 0.01,
                "layers": [64, 32, 16]
            },
            "training": {
                "batch_size": 32,
                "epochs": 10
            }
        }
        dict_config = OmegaConf.create(config_dict)
        
        # This should be flattened for database storage
        exp = TestExperiment(pm, "dictconfig_exp", dict_config)
        results = exp()
        
        print(f"✓ DictConfig worked")
        print(f"  Original type: {type(dict_config)}")
        print(f"  Converted type: {type(exp.config)}")
        print(f"  Config: {exp.config}")
        return True
        
    except Exception as e:
        print(f"✗ DictConfig test failed: {e}")
        return False
    finally:
        os.chdir("..")
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("="*60)
    print("Testing Hydra Support")
    print("="*60)
    
    results = []
    results.append(test_plain_dict())
    results.append(test_dict_config())
    
    print("\n" + "="*60)
    if all(results):
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")