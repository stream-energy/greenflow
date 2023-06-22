#!/usr/bin/env python3

import ansible_runner

from .factors import factors
from .state import get_deployment_state_vars, get_experiment_state_vars


def playbook(playbook, extra):
    from .g import g

    ansible_runner.run(
        playbook=playbook,
        private_data_dir=f"{g.gitroot}/ansible",
        extravars=extra,
    )


def base():
    playbook("base.yaml", extra=get_deployment_state_vars())


def prometheus():
    playbook("prometheus.yaml", extra=get_deployment_state_vars())


def scaphandre():
    playbook("scaphandre.yaml", extra=get_deployment_state_vars())


def deploy_k3s():
    playbook("deploy_k3s.yaml", extra=get_deployment_state_vars())


def strimzi():
    playbook("strimzi.yaml", extra=get_deployment_state_vars())


def theodolite():
    playbook("theodolite.yaml", extra=get_deployment_state_vars())


def exp():
    from .g import g

    g.init_exp()
    playbook(
        "generate_experiment.yaml",
        extra=get_deployment_state_vars() | get_experiment_state_vars() | factors(),
    )
    playbook(
        "_current_exp.yaml",
        extra=get_deployment_state_vars() | get_experiment_state_vars() | factors(),
    )
    g.end_exp()
