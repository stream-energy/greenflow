# Introduction

GreenFlow is a comprehensive toolkit designed to facilitate experiments measuring energy consumption in distributed cloud settings. Typically run in data center environments, it leverages a cloud-native workflow using Kubernetes, enabling precise measurement and attribution of power consumption to specific processes and nodes through the Scaphandre toolkit.

## System Overview

GreenFlow consists of several key components working together to provide a robust experimental framework:

1. **Core Python Package**: Contains the main logic for orchestration, state handling, and experiment storage.

2. **Entrypoint**: The `entrypoint.py` file serves as the main entry point for running experiments. It handles command-line interactions and imports necessary modules. 

3. **Configuration Management**: Utilizes the Gin library for dependency injection and configuration management.

4. **Prometheus Integration**: Used for monitoring and data collection, with support for remote write capability. See [Prometheus Setup](./prometheus-setup.md) for more information.

For a complete overview of the system architecture, see [System Overview](./overview.md).

## Energy Measurement with Scaphandre

GreenFlow leverages Scaphandre for detailed energy breakdowns. Key points to note:

- Relies on Intel RAPL (Running Average Power Limit) technology.
- Requires a recent Linux kernel with PowerCap interface enabled.
- Needs bare-metal access to the cluster for CPU register access.
- Measures energy consumption for CPU and RAM, but not peripherals, storage, or cooling systems.

For more on energy measurement, see the [Scaphandre documentation](https://hubblo-org.github.io/scaphandre/book/compatibility.html)

## Workflow Overview

GreenFlow's workflow, primarily designed for the Grid'5000 testbed, involves:

1. **Provisioning**: Making reservations using OAR Job system to obtain bare-metal hardware resources
2. **Deployment of Kubernetes**: GreenFlow makes use of the K3S distribution
3. **Infrastructure Deployment**: Setting up Scaphandre, Prometheus, and other necessary services.
4. **Experiment Execution**: Running one or more experiments within a deployment.
5. **Data Collection and Analysis**: Collecting and analyzing experiment results.
6. **Tear Down**: All the resources are destroyed and released.

For a detailed explanation of the workflow, refer to [Workflow Overview](./workflow.md).

## Getting Started

To begin using GreenFlow:

1. Review the [Requirements](./requirements.md) for running GreenFlow.
2. Learn how to design and run experiments in [Running Experiments](./workflow.md).
3. Understand how to analyze your results in [Data Collection and Analysis](./data-analysis.md).


By following this documentation, you'll be able to run reproducible experiments to measure and analyze energy consumption in distributed systems using GreenFlow.
