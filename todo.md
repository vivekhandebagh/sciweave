# Rex Framework - Todo List

## 1. Fix Immediate Issues
- [ ] Fix indentation error in project_manager.py (line 13)
- [ ] Run tests to verify current functionality works

## 2. Core Functionality

### Hydra Integration
- [ ] Create HydraExperiment class that bridges Hydra configs with Rex
- [ ] Handle nested config flattening for database storage
- [ ] Support config storage as both flat params and full YAML/JSON

### Result Directory Management  
- [ ] Implement automatic result directory creation (experiment_name/results/timestamp/)
- [ ] Add result_path handling in Experiment class
- [ ] Store directory pointer in database

### Archive/Reset Functions
- [ ] Add `pm.reset_experiment(name)` - creates fresh table, archives old
- [ ] Add `pm.archive_experiment(name)` - moves to archived table
- [ ] Add `pm.new_version(name)` - creates versioned tables (exp_v2, exp_v3)

## 3. API Improvements
- [ ] Create `__init__.py` to enable `import rex`
- [ ] Clean up API to match README vision
- [ ] Add cross-experiment query functionality

## 4. Testing & Documentation
- [ ] Fix and run all tests
- [ ] Update README with actual working examples
- [ ] Add examples directory with sample experiments

## 5. Nice-to-Have (Lower Priority)
- [ ] Integrate schema_manager.py (or remove if not needed)
- [ ] Add experiment comparison tools
- [ ] Add export functionality (CSV, JSON)