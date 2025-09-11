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


# Implementation Notes:
Example codebase:

'''
project-name/
    init_research.py
    visualization_defaults.py
    train-experiments/
        experiment1-name/
            experiment_script.py   
        experiment2-name/
    analysis-experiments/
        experiment3-name/
        experiment4-name/
'''

init_research:
- will initiate the project database. 
- define an experiment class that sets up the table creation routines, default/required schema, and config.
- will need an experiment.config object that will be a dictionary/yaml that will dynamically link to the experiment schema.

Experiment class:
- this will be an abstract class
- when we want to create a new experiment, we can create an experiment that subclasses Experiment. whatever they want for the experiment to run should be defined in the run() abstract method.
- Experiment.__call__() will run all boilerplate code like creating the table, generating run_ids, etc.
- when an experiment is created, it needs to maintain a pointer to the table corresponding to that experiment. this way even if the experiment name is changed or evolves, we still use the same table. or if we spin up multiple instances of the same experiment in parallel, it will write to the same table.
- if run fails, results wont be generated. but the database should still be updated with the pre-results schema and then run status should be updated correctly as "failed" or "interrupted"

result management:
- database will store a pointer to the directory where the results are stored
- all the results you want on the database will be compiled into a dictionary/JSON
- only these results will be added or updated as columns in the table.
- but otherwise, you can store checkpoints, plots, samples, etc. in the exeriment_name/results/time_stamp/ folder

experiment_script:
- the experiment script will create the new experiment object
- set the experiment configuration
- define the actual experiment flow and code that produces results

helper functions that mask basic SQL queries:
- get_results(run_id)
- a run_id() function that returns list of run_ids of a particular timestamp, or corresponding to a time interval, or other filter parameters
