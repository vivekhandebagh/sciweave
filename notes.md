# simplex-research experimental infrastructure plan

How can we create infrastructures and systems level approaches to manage, organize, and easily implement new experiments and ideas? 
How do we take advantage of AI to vibe code experiments in a manner that maintains long term organization? 
As the human researcher, you are responsible for maintaining the long term vision and context of the experiment. Your vibe coding should be about crossing off implementations in your todo list and execution. Often, what happens is that you start with one basic experiment or question that you base your project off of. But almost always, you will end up asking numerous subsequent questions that may require more than just changing certain parameters. So you start implementing more experiments and analysis scripts sequentially. This is fine for most cases. But when you have a long term research vision in a particular field, you will probably be building off of a lot of the same structures and ideas, so you will need thought out systems in place that will accelerate your research. Building with your vibecoding agent constrained by these research protocols will help to actually accelerate your work.


# What is needed?:

- a database that lets you filter, query, organize, and run your experiments in an organized manner

- easily aggregate information and results across runs or experiments and filter by generative process, model architecture, etc.

- experiment runs should be marked as "dev" and "prod"

- should be able to manage the case in which the experiment schema evolves

- tracking of all experiment metadata and run parameters

- simple config system that works with dictionaries or YAML files

- really easy eays to do parameter sweeps

- scaffolding that allows for AI systems to easily find runs, keep context, interface with your research, and implement experiment all while maintaining standardized organization.

- serverless database

# Features to add:

- garbage collection of deprecated experiments and runs

- tag/highlight different runs and mark the ones you consider best for your paper and research

- more error handling

- user should be able to query their research database even if they don't have familiarity with SQL commands.

- need to be able to immediately see your experiment results quickly without having to run SQL queries everytime

- caching and memory optimizations

- pointer to git branch/version/status that tracks experiment version

- if a column in your results is numerical, be able to easily get mean, variance, and other statistics


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
