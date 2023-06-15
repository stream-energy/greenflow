#!/usr/bin/env python3

import ansible_runner

from .factors import factors
from .g import g


def _helper(playbook):
    ansible_runner.run(
        playbook=playbook,
        private_data_dir="./ansible",
        extravars={
            "deployment_start_ts": g.root.current_deployment.started_ts.to_iso8601_string(),
            "kubeconfig_path": "../../kubeconfig",
        },
    )


def exp():
    _helper("exp.yaml")


def base():
    _helper("base.yaml")


def deploy_k3s():
    _helper("deploy_k3s.yaml")


def strimzi():
    _helper("strimzi.yaml")
