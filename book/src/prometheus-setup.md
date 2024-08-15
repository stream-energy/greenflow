# Prometheus Setup

This document outlines the setup process for Prometheus within the GreenFlow project, explaining how it integrates with other components and the configuration required for successful deployment.

## Overview

The Prometheus setup in GreenFlow is designed to collect metrics from experiments run on a Kubernetes cluster and store them in a local Docker Compose environment. This setup allows for flexible data collection and analysis agnostic to the network.

## Motivation

The approach taken in GreenFlow for setting up Prometheus and related components is driven by several key factors:

1. **Network Agnosticism**: Experiments may be run on various types of machines with different network configurations. This setup ensures consistency across different environments without requiring complex network setups.

2. **Ephemeral Experiment Environments**: GreenFlow is designed to run on bare metal platforms with ephemeral nodes and reservations. No data is stored permanently on the cluster itself, necessitating a reliable external data collection solution.

3. **Simplified Setup**: By leveraging Docker and Nix on the local machine, we ensure that experiments can be run without the need for a custom domain or a personally managed Prometheus server exposed to the web.

4. **Flexibility**: This approach allows for data collection and analysis even when the experimental nodes are not on the same network as the analysis machine.

5. **Reproducibility**: The consistent interface provided by this setup enhances the reproducibility of experiments across different configurations and environments.

6. **Data Persistence**: While the experiment environment is ephemeral, this setup ensures that valuable metrics and data are safely stored and accessible for post-experiment analysis.

By addressing these challenges, we provide a robust and reliable solution that simplifies the complexity of setting up experiments in diverse environments while ensuring data integrity and accessibility.

## Key Components

1. Prometheus Helm Chart (deployed on Kubernetes, within the experimental cluster)
2. Local Docker Compose environment
3. Tailscale for secure networking

## Deployment Process

### 1. Kubernetes Prometheus Setup

The Prometheus stack is deployed on the Kubernetes cluster using a Helm chart. This Prometheus instance is configured to scale up before an experiment starts and scale down after it completes.

This configuration is part of the Ansible role `prometheus` and the values of the Helm chart are substituted in `$PROJECT_ROOT/ansible/project/roles/prometheus/templates/kube-prometheus-stack-values.yaml.j2`
Key configuration:

- Remote Write URL: This is set to point to the local Victoria Metrics instance.

### 2. Local Docker Compose Environment

The local environment runs several services:

- Victoria Metrics: Acts as the target Prometheus cluster, receiving data from the Kubernetes Prometheus instance.
- Grafana: For visualizing the collected metrics.
- Caddy: Reverse proxy for routing requests.
- Tailscale: Provides secure networking between the Kubernetes cluster and local environment.

### 3. Tailscale Configuration

Tailscale is used to create a secure connection between the Kubernetes cluster and the local machine. This is especially useful when the local machine is behind NAT or firewalls.

## Configuration

Most of the user-specific configuration is captured in the `.secrets.env` file. This file is used by Ansible templates to populate the necessary values in the Prometheus role. After making any changes, make sure to run `direnv allow` or manually source the variables by running `source .secrets.env`

Key configurations in `$PROJECT_ROOT/.secrets.env`.

### Tailscale Setup

1. Set up a [Tailscale account](https://login.tailscale.com/admin/machines).
2. Generate a [Tailscale auth key](https://login.tailscale.com/admin/settings/keys)
3. Add the Tailscale auth key to the .env file in the Docker Compose directory `$PROJECT_ROOT/deploy`

### How does it work?

1. Before an experiment:
   The Prometheus stack in Kubernetes scales up.
2. During the experiment:
   ▪ Metrics are collected by the Kubernetes Prometheus instance.
   ▪ Data is also sent to the local Victoria Metrics instance via the [Prometheus Remote Write API](https://prometheus.io/docs/specs/remote_write_spec/)
3. After the experiment:
   ▪ The Kubernetes Prometheus stack scales down.
   ▪ Data remains in the local Victoria Metrics for analysis.

### Alternative Access Methods

While Tailscale is recommended for its ease of use and security, alternative methods for accessing the Kubernetes cluster from the local machine include:
- ngrok
- Cloudflare Tunnel
- Direct access (if the local machine is accessible from all nodes of the Kubernetes cluster and firewall/ports are open)
