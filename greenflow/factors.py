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
    kafkaOnWorker: bool = gin.REQUIRED,
):
    return {
        "warmupSeconds": warmupSeconds,
        "durationSeconds": durationSeconds,
        "instances": instances,
        "kafkaOnWorker": kafkaOnWorker,
        "load": load,
    }
