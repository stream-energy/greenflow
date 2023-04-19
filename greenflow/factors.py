#!/usr/bin/env python3
import json
from shlex import split

import ansible_runner
import gin
import pendulum
from sh import ansible_playbook, rm

from .g import g
from .g5k import G5KPlatform
from .platform import MockPlatform, Platform


@gin.configurable
def factors(
    *,
    kafkaOnWorker: bool = True,
    uc1_flink_resourceValue: int = 64,
    uc1_flink_loadValue: int = 100000,
    uc3_flink_loadValue: int = 100000,
    uc3_flink_resourceValue: int = 64,
    duration: int = 300,
    # *,
    # base_num_workers: int,
    # base_num_control: int,
    # uc1_flink_taskmanager_resources: int,
):
    return {
        "kafkaOnWorker": kafkaOnWorker,
        "uc1_flink_loadValue": uc1_flink_loadValue,
        "uc1_flink_loadValue": uc1_flink_loadValue,
        "uc1_flink_resourceValue": uc1_flink_resourceValue,
        "uc3_flink_resourceValue": uc3_flink_resourceValue,
        "uc3_flink_loadValue": uc3_flink_loadValue,
        "duration": duration,
    }
