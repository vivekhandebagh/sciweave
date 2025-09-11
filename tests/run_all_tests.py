#!/usr/bin/env python3
"""
Main test runner for the experiment infrastructure
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_project_manager import TestProjectManager
from test_experiment import TestExperimentClass


def run_all_tests():
    """Run all test suites and compile results"""
    
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'test_suites': {},
        'summary': {
            'total_passed': 0,
            'total_failed': 0
        }
    }
    
    print("\n" + "="*80)
    print("EXPERIMENT INFRASTRUCTURE TEST SUITE")
    print("="*80)
    
    # Run ProjectManager tests
    print("\nRunning ProjectManager tests...")
    pm_tester = TestProjectManager()
    try:
        pm_results = pm_tester.run_all_tests()
        all_results['test_suites']['ProjectManager'] = {
            'passed': pm_tester.passed,
            'failed': pm_tester.failed,
            'tests': pm_results
        }
        all_results['summary']['total_passed'] += pm_tester.passed
        all_results['summary']['total_failed'] += pm_tester.failed
    except Exception as e:
        print(f"ProjectManager tests failed with exception: {e}")
        all_results['test_suites']['ProjectManager'] = {
            'error': str(e)
        }
    finally:
        pm_tester.cleanup()
    
    # Run Experiment tests
    print("\nRunning Experiment class tests...")
    exp_tester = TestExperimentClass()
    try:
        exp_results = exp_tester.run_all_tests()
        all_results['test_suites']['Experiment'] = {
            'passed': exp_tester.passed,
            'failed': exp_tester.failed,
            'tests': exp_results
        }
        all_results['summary']['total_passed'] += exp_tester.passed
        all_results['summary']['total_failed'] += exp_tester.failed
    except Exception as e:
        print(f"Experiment tests failed with exception: {e}")
        all_results['test_suites']['Experiment'] = {
            'error': str(e)
        }
    finally:
        exp_tester.cleanup()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests Passed: {all_results['summary']['total_passed']}")
    print(f"Total Tests Failed: {all_results['summary']['total_failed']}")
    
    if all_results['summary']['total_failed'] == 0:
        print("\n✓ ALL TESTS PASSED!")
    else:
        print(f"\n✗ {all_results['summary']['total_failed']} tests failed")
    
    return all_results


if __name__ == "__main__":
    results = run_all_tests()
    
    # Save results to JSON for further analysis
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)