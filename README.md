
# WORKFLOW:


```
import rex
from rex import ProjectManager
import hydra
from omegaconf import DictConfig
# initialize/activate project manager (which is essentially anchored to a project_name.db file)
pm = ProjectManager(project_name)

# define your experiment logic
class MyExperiment(rex.Experiment):
    def __init__(self):
        pass

    def run(self):
        # experiment logic
        return results

# set your config (either as a dictionary or through Hydra)
@hydra.main(config_path="conf", config_name="config")
def main(cfg: DictConfig):
    exp = MyExperiment(pm="sqlite", name=cfg.experiment.name, config=cfg)
    results = exp()
```


STACK:
Hydra (configuration management)
Experiment (defined by a config, experiment logic in run(), results)
Interface/schema manager (handles evolving experiments, formatting configs/results, etc.)
Project Manager (database of experiments.)


EXPERIMENT CLASS:
- this will be an abstract class
- when we want to create a new experiment, we can create an experiment that subclasses Experiment. 
- whatever they want for the experiment to run should be defined in the run() abstract method.
- Experiment.__call__() will run all boilerplate code that deals with updating all information to the database before and after calling self.run()
- when an experiment is created, it needs to be updated to the database's experiment registry and maintained there. 


RESULT MANAGEMENT:
- database will store a pointer to the directory where all results of a particular run are stored
- all the results you want on the database should be compiled into a dictionary/JSON
- only these results will be added or updated as columns in the table.
- but otherwise, all results of a run will be stored in a local folder. 
- but otherwise, you can store checkpoints, plots, samples, etc. in the exeriment_name/results/time_stamp/folder


SCHEMA MANAGER/UTILS(this doesn't necessarily have to be a separate class or file. it could just be an aspect of project manager):
- helper functions that mask wrap/mask SQL queries
- converting and formatting Experiment configs for database (Hydra is something the user may or may not use. Deal with configs that are purely standard dictionaries or are omegaconf.DictConfigs.)
- identifying when and how experiment evolves, making sure that is reflected in the database schema updates
    - simple column update
    - reset experiment database
    - create versioning?


PROJECT MANAGER:
- is basically the project's .db file
- maintains the experiment registry
- query your experiments
- query across your experiments
