# Rex Framework - Todo List

## 1. Fix Immediate Issues
- [x] Fix indentation error in project_manager.py (line 13)
- [x] Run tests to verify current functionality works

## 2. Core Functionality

### Experiment
- [x] allow for experiment config to be a dictionary or a DictConfig (to allow for Hydra)


### Config to Database Interface
- [ ] create a blank interface layer that will handle validation, handles formatting, handles formatting.
- [x] if config is heirarchical, it needs to be flattened for schema
- [ ] identify how config/schema evolves

### Archive/Reset Functions
- [ ] Add `pm.reset_experiment(name)` - creates fresh table, archives old
- [ ] Add `pm.archive_experiment(name)` - moves to archived table
- [ ] Add `pm.new_version(name)` - creates versioned tables (exp_v2, exp_v3)
- [ ] Brainstorm and Implement garbage collection routines

### Result Directory Management  
- [ ] Implement automatic result directory creation (experiment_name/results/timestamp/)
- [ ] Add result_path handling in Experiment class
- [ ] Store directory pointer in database

## 3. API Improvements
- [ ] Organize better. What should go in Project Manager, Utils, etc.
- [ ] Create `__init__.py` to enable `import rex`
- [ ] Clean up API to match README vision
- [ ] Add cross-experiment query functionality

## 4. Testing & Documentation
- [ ] Fix and run all tests
- [ ] Update README with actual working examples
- [ ] Add examples directory with sample experiments

## 5. Nice-to-Have (Lower Priority)
- [ ] Add experiment comparison tools
- [ ] Add export functionality (CSV, JSON)