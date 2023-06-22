#!/usr/bin/env python3

import gin


@gin.configurable
def factors(
    *,
    experiment_name: str = gin.REQUIRED,
    experiment_params: dict = gin.REQUIRED,
) -> dict:
    return dict(
        {
            "experiment_name": experiment_name,
            "experiment_params": experiment_params,
        }
    )
