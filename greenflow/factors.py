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
    broker_cpu: int = gin.REQUIRED,
    broker_io_threads: int = gin.REQUIRED,
    broker_mem: str = gin.REQUIRED,
    broker_network_threads: int = gin.REQUIRED,
    broker_replica_fetchers: int = gin.REQUIRED,
    broker_replicas: int = gin.REQUIRED,
    consumer_instances: int = gin.REQUIRED,
    durationSeconds: int = gin.REQUIRED,
    kafka_bootstrap_servers: str = gin.REQUIRED,
    load: int = gin.REQUIRED,
    messageSize: int = gin.REQUIRED,
    partitions: int = gin.REQUIRED,
    producer_instances: int = gin.REQUIRED,
    redpanda_write_caching: bool = True,
    replicationFactor: int = gin.REQUIRED,
    topic_name: str = gin.REQUIRED,
    warmupSeconds: int = gin.REQUIRED,
):
    return {
        "broker_cpu": broker_cpu,
        "broker_io_threads": broker_io_threads,
        "broker_mem": broker_mem,
        "broker_network_threads": broker_network_threads,
        "broker_replica_fetchers": broker_replica_fetchers,
        "broker_replicas": broker_replicas,
        "consumer_instances": consumer_instances,
        "durationSeconds": durationSeconds,
        "kafka_bootstrap_servers": kafka_bootstrap_servers,
        "load": load,
        "messageSize": messageSize,
        "partitions": partitions,
        "producer_instances": producer_instances,
        "redpanda_write_caching": redpanda_write_caching,
        "replicationFactor": replicationFactor,
        "topic_name": topic_name,
        "warmupSeconds": warmupSeconds,
    }
