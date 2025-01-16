#!/usr/bin/env python3

from typing import Any
import gin


@gin.configurable
def factors(
    *,
    exp_name: str = gin.REQUIRED,
) -> dict[str, Any]:
    return {
        "exp_name": exp_name,
        "exp_params": exp_params(),
    }


@gin.configurable
def exp_params(
    *,
    warmupSeconds: int = gin.REQUIRED,
    durationSeconds: int = gin.REQUIRED,
    producer_instances: int = gin.REQUIRED,
    consumer_instances: int = gin.REQUIRED,
    load: int = gin.REQUIRED,
    messageSize: int = gin.REQUIRED,
    replicationFactor: int = gin.REQUIRED,
    partitions: int = gin.REQUIRED,
    redpanda_write_caching: bool = True,
    kafka_bootstrap_servers: str = gin.REQUIRED,
    broker_cpu: int = gin.REQUIRED,
    broker_replicas: int = gin.REQUIRED,
    broker_mem: str = gin.REQUIRED,
    broker_io_threads: int = gin.REQUIRED,
    broker_network_threads: int = gin.REQUIRED,
):
    return {
        "warmupSeconds": warmupSeconds,
        "durationSeconds": durationSeconds,
        "producer_instances": producer_instances,
        "consumer_instances": consumer_instances,
        "messageSize": messageSize,
        "replicationFactor": replicationFactor,
        "partitions": partitions,
        "kafka_bootstrap_servers": kafka_bootstrap_servers,
        "redpanda_write_caching": redpanda_write_caching,
        "load": load,
        "broker_cpu": broker_cpu,
        "broker_replicas": broker_replicas,
        "broker_mem": broker_mem,
        "broker_io_threads": broker_io_threads,
        "broker_network_threads": broker_network_threads,
    }
