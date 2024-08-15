# System Overview

## Entry Point

The main entry point for running and managing experiments is `$PROJECT_ROOT/entrypoint.py`. This script provides CLI commands for setting up the environment, running experiments, and managing resources.

The entrypoint is meant to be edited and modified by the experimenter. There is some limited capability to pass in command-line arguments, however, for more complex usecases, it's meant to be easy to change.

### Experiment Management

Experiments are managed using the `Experiment` class in `$PROJECT_ROOT/greenflow/experiment.py`. This class handles the initialization, execution, and result calculation of experiments.

### Configuration

As stream processing systems have a large number of configuration parameters and tuneables, this project uses [gin-config](https://github.com/google/gin-config) for configuration management. Refer `$PROJECT_ROOT/gin` for more.

Gin is a lightweight, Python-like configuration language that supports dependency injection. This allows us to define functions without explicitly passing each and every parameter that might change.

Configurations are defined in `.gin` files and can be dynamically re-bound using the `rebind_parameters` function in `entrypoint.py`.

### Storage

Experiment data is stored using TinyDB with custom serialization for handling complex data types. The `ExpStorage` class in `storage.py` manages the experiment database.

The experiment database is stored in plain-text in `yaml` format at `$PROJECT_ROOT/storage/experiment-history.yaml`. This includes any and all parameters, the Grid'5000 deployment information as well as the exact timestamps of `experiment_started_ts` and `deployment_started_ts` which are then used correspondingly as labels with the VictoriaMetrics/Prometheus TSDB to filter the results for further analysis. For more details, click [here](./setup/prometheus-setup.md).

### What next?

Now that you have a better idea of how the overall system works, [let's understand the overall workflow](./workflow.md).
