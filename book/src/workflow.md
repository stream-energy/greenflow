# Workflow

## Entrypoint

The `$PROJECT_ROOT/entrypoint.py` is meant to be readable and editable and customisable and provide an easy way to run various experiments and expose it as a command-line interface to be able to pass in parameters.

## Workflow Steps

### 1. Setting Up the Environment

**Objective**: Provision resources, deploy necessary services, and prepare the environment for experiments.

**Command**:

```sh
python entrypoint.py setup <exp_name> --workers <num_workers>
```

Details:

- Provision Resources: This step provisions the required resources (e.g., VMs or containers) and sets up the Kubernetes cluster if not already present.
- Deploy Services: Deploys essential services like Prometheus, Scaphandre, Kafka, and Redpanda.
- Warm-up: Initializes Kafka and Redpanda to ensure they are ready for experiments.
  Note:
- At its base, the G'5K provider is provided and is the main focus for the Greenflow project. However, provisioning is Customisable by implementing the `platform` interface (`$PROJECT_ROOT/greenflow/platform.py`)
- If you already have a pre-existing set of nodes/VMs for the cluster, you can skip the provisioning step. Instead, run the `deploy_k3s` after setting up `$PROJECT_ROOT/ansible/inventory/hosts.yaml` in a similar format to the one below.

```yaml
all:
  children:
    broker:
      hosts:
        paravance-68.rennes.grid5000.fr:
          kubernetes_role: broker
        paravance-8.rennes.grid5000.fr:
          kubernetes_role: broker
        paravance-9.rennes.grid5000.fr:
          kubernetes_role: broker
    control:
      hosts:
        paravance-14.rennes.grid5000.fr:
          kubernetes_role: control_plane
    worker:
      hosts:
        paravance-16.rennes.grid5000.fr:
          kubernetes_role: node
        paravance-25.rennes.grid5000.fr:
          kubernetes_role: node
        paravance-32.rennes.grid5000.fr:
          kubernetes_role: node
```

#### Roles in the Cluster

The `hosts.yaml` file defines different roles for the nodes in the cluster:

1. **broker**: These nodes are dedicated to running Kafka or Redpanda brokers. They handle message storage and distribution.

2. **control_plane**: This node (or nodes) manages the Kubernetes cluster operations. It's responsible for maintaining the desired state of the cluster. It also serves as the metrics server, and all of the Kubernetes operators.

3. **worker**: These nodes run the actual workloads (pods) in the Kubernetes cluster.

This separation of roles allows for better resource allocation and performance optimization based on the specific requirements of each component.

### 2. Running Experiments

Objective: Execute experiments with specified configurations to measure energy consumption.

```
python entrypoint.py ingest <exp_name> --load <load> --message_size <size> --instances <instances> --partitions <partitions>
```

Details:
• Configuration: Load the appropriate configuration using load_gin.
• Execution: Run the experiment using the ingest command with specified parameters.
• Monitoring: The results are [automatically collected](./setup/prometheus-setup.md) and written to the local (and `remote_write`) Prometheus/VictoriaMetrics server.
Objective: Terminate the current job and clean up resources.
Command:

python entrypoint.py killjob
Details:
• This step ensures that all resources are properly cleaned up after the experiment.
Interactive Shell
Objective: Provide a flexible environment for running setup steps and experiments without provisioning.
Command:

python entrypoint.py i <exp_name>
Details:
• Direct Access: Drop into an interactive shell with the current experiment configuration.
• Custom Setup: Run any setup steps manually, deploy specific services, or configure parameters as needed.
Customizing the Workflow
GreenFlow's workflow is highly customizable. Here are some key points to consider:
Pre-existing Kubernetes Cluster
• If you already have a Kubernetes cluster, you can skip the provisioning step in the setup.
• Use the interactive shell to deploy necessary services and configure your environment.
Deploying Theodolite
• Theodolite provides various use cases for stream processing systems.
• Deploy Theodolite using its playbook and configure it for specific use cases like UC1 Flink.
• For more details, refer to the Theodolite documentation.
Running Custom Workflows
• If you have a custom workflow, package your script into a Docker container and create a Kubernetes manifest.
• Use the provided playbooks to set up the necessary environment (e.g., Prometheus stack).
• Customize the experiment.yaml meta-template to define your experiment.
Example Workflow

```
```
# Running an Experiment

Currently the only workflow tested is to run an experiment specified in the meta-template `$PROJECT_ROOT/project/templates/exp.yaml.j2`. With a basic knowledge of Ansible, you can modify it and call the corresponding playbook from `entrypoint.py`.


```
python entrypoint.py setup ingest-kafka --workers 3 #reserves nodes, sets up k3s, deploys all helm charts
python entrypoint.py ingest ingest-kafka # Runs the experiment specified under the ingest cli in entrypoint.py
```
## Using Interactive Shell
If you have a pre-existing Kubernetes cluster:

```
python entrypoint.py i ingest-kafka
```

In the interactive shell, you can run setup steps manually:

```sh
# Load configuration
load_gin(exp_name="ingest-kafka")
# Deploy Prometheus
p(prometheus)
# Deploy Kafka
p(kafka)
# Deploy Redpanda
p(redpanda)
# Deploy Theodolite
```
Conclusion
GreenFlow provides a flexible and customizable workflow for running energy consumption experiments. By understanding the key steps and leveraging the interactive shell, you can efficiently set up, run, and clean up your experiments. Customize the workflow to fit your specific needs and experiment configurations.

```

```
