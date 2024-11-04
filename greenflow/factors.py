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
    instances: int = gin.REQUIRED,
    load: int = gin.REQUIRED,
    messageSize: int = gin.REQUIRED,
    replicationFactor: int = gin.REQUIRED,
    partitions: int = gin.REQUIRED,
    redpanda_write_caching: bool = True,
    kafka_bootstrap_servers: str = gin.REQUIRED,
    broker_cpu: str = gin.REQUIRED,
    broker_mem: str = gin.REQUIRED,
):
    return {
        "warmupSeconds": warmupSeconds,
        "durationSeconds": durationSeconds,
        "instances": instances,
        "messageSize": messageSize,
        "replicationFactor": replicationFactor,
        "partitions": partitions,
        "kafka_bootstrap_servers": kafka_bootstrap_servers,
        "redpanda_write_caching": redpanda_write_caching,
        "load": load,
        "broker_cpu": broker_cpu,
        "broker_mem": broker_mem,
    }
