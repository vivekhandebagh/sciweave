#!/usr/bin/env python3
"""
Comprehensive demo of SciWeave framework capabilities.
This script demonstrates:
- Creating multiple experiments
- Running experiments with different configs
- Schema evolution (adding new parameters and metrics)
- Querying within and across experiments
- Using tags and notes
- Finding best performing runs
"""

import sys
import os
import random
import time
from datetime import datetime, timedelta

# Add parent directory to path if running from repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from project_manager import ProjectManager
from experiment import Experiment


# ==============================================================================
# Define Different Types of Experiments
# ==============================================================================

class OptimizationExperiment(Experiment):
    """Simulates an optimization problem (e.g., finding minimum of a function)"""
    
    def run(self):
        # Simulate optimization with some randomness
        lr = self.config.get('learning_rate', 0.01)
        iterations = self.config.get('iterations', 100)
        momentum = self.config.get('momentum', 0.0)  # May not always be present
        
        # Simulate some computation
        base_loss = 1.0 / (1 + 10 * lr + 5 * momentum)
        noise = random.gauss(0, 0.1)
        final_loss = max(0.01, base_loss + noise)
        
        # Calculate convergence speed (made up metric)
        convergence_speed = iterations * lr * (1 + momentum)
        
        results = {
            'final_loss': round(final_loss, 4),
            'converged': final_loss < 0.5,
            'convergence_speed': round(convergence_speed, 2)
        }
        
        # Sometimes we might track additional metrics
        if self.config.get('track_gradients', False):
            results['gradient_norm'] = round(random.uniform(0.001, 0.1), 4)
        
        return results


class SimulationExperiment(Experiment):
    """Simulates a physics/biology simulation with different parameters"""
    
    def run(self):
        # Get simulation parameters
        timestep = self.config.get('timestep', 0.01)
        particles = self.config.get('num_particles', 1000)
        temperature = self.config.get('temperature', 300)
        
        # Simulate some physics
        energy = particles * temperature * 1.38e-23  # Fake physics
        stability = 1.0 / (1 + timestep * 10)
        
        results = {
            'total_energy': round(energy * 1e20, 2),
            'stability_score': round(stability, 3),
            'simulation_time': round(random.uniform(0.5, 5.0), 2)
        }
        
        # Schema evolution: later runs might track more metrics
        if self.config.get('detailed_analysis', False):
            results['entropy'] = round(random.uniform(0, 1), 3)
            results['phase_transition'] = random.choice([True, False])
        
        return results


class MLModelExperiment(Experiment):
    """Simulates training a machine learning model"""
    
    def run(self):
        # Model hyperparameters
        model_type = self.config.get('model', 'linear')
        lr = self.config.get('learning_rate', 0.001)
        batch_size = self.config.get('batch_size', 32)
        epochs = self.config.get('epochs', 10)
        
        # Simulate training with some logic
        if model_type == 'neural_net':
            base_acc = 0.85
        elif model_type == 'random_forest':
            base_acc = 0.80
        else:  # linear
            base_acc = 0.75
        
        # Learning rate affects accuracy
        accuracy = min(0.99, base_acc + lr * 10 + random.gauss(0, 0.05))
        
        # Batch size affects training time
        train_time = epochs * (1000 / batch_size) + random.uniform(0, 10)
        
        results = {
            'accuracy': round(accuracy, 4),
            'training_time': round(train_time, 2),
            'val_accuracy': round(accuracy - random.uniform(0.01, 0.05), 4)
        }
        
        # Later versions might track more metrics
        if self.config.get('track_loss', False):
            results['final_loss'] = round(1 - accuracy + random.gauss(0, 0.01), 4)
            results['val_loss'] = round(1 - results['val_accuracy'], 4)
        
        # Even later: add F1 score
        if self.config.get('compute_f1', False):
            results['f1_score'] = round(accuracy - random.uniform(0, 0.02), 4)
        
        return results


# ==============================================================================
# Main Demo Script
# ==============================================================================

def main():
    print("=" * 80)
    print("SCIWEAVE FRAMEWORK DEMO")
    print("=" * 80)
    
    # Initialize project
    print("\n📁 Initializing project 'research_demo'...")
    pm = ProjectManager("research_demo")
    
    # ==============================================================================
    # PART 1: Run basic experiments
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 1: Running Basic Experiments")
    print("=" * 80)
    
    # Run optimization experiments with different configs
    print("\n🔬 Running optimization experiments...")
    for lr in [0.01, 0.05, 0.1, 0.5]:
        for iterations in [100, 500]:
            config = {
                'learning_rate': lr,
                'iterations': iterations,
                'algorithm': 'gradient_descent'
            }
            exp = OptimizationExperiment(pm, "optimization_study", config)
            result = exp()
            print(f"  LR={lr}, iter={iterations} -> loss={result.get('final_loss', 'N/A')}")
    
    # Run simulation experiments
    print("\n🌊 Running simulation experiments...")
    for particles in [100, 1000, 10000]:
        for temp in [100, 300, 500]:
            config = {
                'num_particles': particles,
                'temperature': temp,
                'timestep': 0.01
            }
            exp = SimulationExperiment(pm, "particle_simulation", config)
            result = exp()
            print(f"  Particles={particles}, T={temp}K -> energy={result.get('total_energy', 'N/A')}")
    
    # Run ML experiments
    print("\n🤖 Running ML model experiments...")
    for model in ['linear', 'neural_net', 'random_forest']:
        for lr in [0.001, 0.01]:
            config = {
                'model': model,
                'learning_rate': lr,
                'batch_size': 32,
                'epochs': 10
            }
            exp = MLModelExperiment(pm, "model_comparison", config)
            result = exp()
            print(f"  Model={model}, LR={lr} -> acc={result.get('accuracy', 'N/A')}")
    
    # ==============================================================================
    # PART 2: Schema Evolution - Add new fields over time
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 2: Schema Evolution")
    print("=" * 80)
    
    # Run optimization with new parameter (momentum)
    print("\n🔄 Evolving optimization experiment with momentum...")
    for momentum in [0.0, 0.9, 0.99]:
        config = {
            'learning_rate': 0.01,
            'iterations': 200,
            'momentum': momentum,  # New parameter!
            'algorithm': 'sgd_momentum'
        }
        exp = OptimizationExperiment(pm, "optimization_study", config)
        result = exp()
        print(f"  Momentum={momentum} -> loss={result.get('final_loss', 'N/A')}")
    
    # Run optimization with gradient tracking
    print("\n📊 Adding gradient tracking to optimization...")
    config = {
        'learning_rate': 0.01,
        'iterations': 200,
        'momentum': 0.9,
        'track_gradients': True,  # This will add gradient_norm to results
        'algorithm': 'sgd_momentum'
    }
    exp = OptimizationExperiment(pm, "optimization_study", config)
    result = exp()
    print(f"  With gradient tracking -> gradient_norm={result.get('gradient_norm', 'N/A')}")
    
    # Run ML with loss tracking
    print("\n📈 Adding loss tracking to ML experiments...")
    config = {
        'model': 'neural_net',
        'learning_rate': 0.01,
        'batch_size': 64,
        'epochs': 20,
        'track_loss': True  # This will add loss metrics
    }
    exp = MLModelExperiment(pm, "model_comparison", config)
    result = exp()
    print(f"  Loss tracking -> final_loss={result.get('final_loss', 'N/A')}")
    
    # Run ML with F1 score
    print("\n🎯 Adding F1 score computation...")
    config['compute_f1'] = True  # This will add f1_score
    exp = MLModelExperiment(pm, "model_comparison", config)
    result = exp()
    print(f"  F1 tracking -> f1_score={result.get('f1_score', 'N/A')}")
    
    # ==============================================================================
    # PART 3: Tagging and Annotations
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 3: Tagging and Annotations")
    print("=" * 80)
    
    # Tag some of the best runs
    print("\n🏷️  Tagging best optimization runs...")
    best_runs = pm.query("optimization_study", 
                         filters={"final_loss": "<0.3"}, 
                         targets=['run_id', 'final_loss'])
    for run in best_runs[:3]:
        pm.add_tags("optimization_study", run['run_id'], ["best", "low_loss"])
        print(f"  Tagged {run['run_id']} (loss={run['final_loss']})")
    
    # Add notes to specific runs
    if best_runs:
        pm.add_notes("optimization_study", best_runs[0]['run_id'], 
                    "This configuration achieved the best convergence")
    
    # ==============================================================================
    # PART 4: Querying Experiments
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 4: Querying Experiments")
    print("=" * 80)
    
    # Query 1: Find all optimization runs with low loss
    print("\n🔍 Query 1: Find optimization runs with loss < 0.5")
    good_runs = pm.query("optimization_study", 
                        filters={"final_loss": "<0.5"},
                        targets=['learning_rate', 'momentum', 'final_loss'])
    print(f"  Found {len(good_runs)} runs with low loss")
    if good_runs:
        for run in good_runs[:3]:
            print(f"    LR={run.get('learning_rate')}, momentum={run.get('momentum', 'N/A')}, "
                  f"loss={run.get('final_loss')}")
    
    # Query 2: Find best ML models
    print("\n🔍 Query 2: Find top 5 ML models by accuracy")
    best_models = pm.get_best_runs("model_comparison", metric="accuracy", n=5)
    for i, run in enumerate(best_models[:3], 1):
        print(f"  #{i}: {run.get('model')} - accuracy={run.get('accuracy')}")
    
    # Query 3: Query by specific config
    print("\n🔍 Query 3: Find all neural network runs")
    nn_runs = pm.query("model_comparison",
                      filters={"model": "neural_net"},
                      targets=['accuracy', 'training_time', 'f1_score'])
    print(f"  Found {len(nn_runs)} neural network runs")
    if nn_runs:
        avg_acc = sum(r['accuracy'] for r in nn_runs) / len(nn_runs)
        print(f"  Average accuracy: {avg_acc:.4f}")
    
    # Query 4: Query by tags
    print("\n🔍 Query 4: Find tagged 'best' runs")
    tagged_runs = pm.get_runs_by_tag("optimization_study", "best")
    print(f"  Found {len(tagged_runs)} runs tagged as 'best'")
    
    # Query 5: Time-based query (get recent runs)
    print("\n🔍 Query 5: Get runs from the last minute")
    recent = pm.query("model_comparison", time_range="week", targets=['run_id', 'accuracy'])
    print(f"  Found {len(recent)} recent ML runs")
    
    # ==============================================================================
    # PART 5: Cross-Experiment Analysis
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 5: Cross-Experiment Analysis")
    print("=" * 80)
    
    # Get summaries for all experiments
    print("\n📊 Experiment Summaries:")
    for exp_name in ["optimization_study", "particle_simulation", "model_comparison"]:
        summary = pm.get_experiment_summary(exp_name)
        print(f"\n  {exp_name}:")
        print(f"    Total runs: {summary['total_runs']}")
        print(f"    Status counts: {summary['status_counts']}")
        if summary['latest_run']:
            print(f"    Latest run: {summary['latest_run']['run_id']} "
                  f"at {summary['latest_run']['time_stamp'][:19]}")
    
    # Compare performance across different experiment types
    print("\n🔬 Analyzing experiment characteristics:")
    
    # Check which optimization algorithm works best
    print("\n  Optimization algorithms comparison:")
    for algo in ['gradient_descent', 'sgd_momentum']:
        runs = pm.query("optimization_study", 
                       filters={'algorithm': algo},
                       targets=['final_loss'])
        if runs:
            avg_loss = sum(r['final_loss'] for r in runs) / len(runs)
            print(f"    {algo}: avg_loss={avg_loss:.4f} ({len(runs)} runs)")
    
    # Check effect of particle count on energy
    print("\n  Particle count vs energy:")
    for n_particles in [100, 1000, 10000]:
        runs = pm.query("particle_simulation",
                       filters={'num_particles': n_particles},
                       targets=['total_energy'])
        if runs:
            avg_energy = sum(r['total_energy'] for r in runs) / len(runs)
            print(f"    {n_particles} particles: avg_energy={avg_energy:.2f}")
    
    # ==============================================================================
    # PART 6: Advanced Queries
    # ==============================================================================
    print("\n" + "=" * 80)
    print("PART 6: Advanced Queries")
    print("=" * 80)
    
    # Complex filter: high accuracy AND low training time
    print("\n🎯 Finding efficient models (high accuracy, low training time):")
    efficient_models = pm.query("model_comparison",
                               filters={'accuracy': '>0.85'},
                               targets='all')
    # Further filter by training time
    efficient_models = [r for r in efficient_models if r.get('training_time', float('inf')) < 150]
    print(f"  Found {len(efficient_models)} efficient models")
    for run in efficient_models[:3]:
        print(f"    {run.get('model')}: acc={run.get('accuracy')}, time={run.get('training_time')}s")
    
    # Show schema evolution
    print("\n📋 Demonstrating schema evolution:")
    all_runs = pm.query("optimization_study", targets='all')
    if all_runs:
        # Check which runs have the new fields
        with_momentum = [r for r in all_runs if r.get('momentum') is not None]
        with_gradients = [r for r in all_runs if r.get('gradient_norm') is not None]
        print(f"  Total optimization runs: {len(all_runs)}")
        print(f"  Runs with momentum field: {len(with_momentum)}")
        print(f"  Runs with gradient tracking: {len(with_gradients)}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("=" * 80)
    print("\n📁 All experiment data has been saved to 'research_demo.db'")
    print("You can continue querying and analyzing this data anytime by loading the same project.")


if __name__ == "__main__":
    main()