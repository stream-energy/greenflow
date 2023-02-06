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
    uc1_flink_resourceValue: int,
    uc1_flink_loadValue: int,
    # *,
    # base_num_workers: int,
    # base_num_control: int,
    # uc1_flink_taskmanager_resources: int,
):
    return {
        "uc1_flink_loadValue": uc1_flink_loadValue,
        "uc1_flink_resourceValue": uc1_flink_resourceValue,
    }


if __name__ == "__main__":
    deploy()
