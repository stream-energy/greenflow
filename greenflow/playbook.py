#!/usr/bin/env python3

import ansible_runner
from sys import exit

from .factors import factors
from .state import get_deployment_state_vars, get_experiment_state_vars


def playbook(playbook, extra):
    from .g import g

    rc = ansible_runner.run(
        playbook=playbook,
        private_data_dir=f"{g.gitroot}/ansible",
        extravars=extra,
        # verbosity=3,
    ).rc
    if rc > 0:
        cleanup()  # Call cleanup function before exit
        exit("Error: Playbook execution interrupted/failed.")

def cleanup():
    # Define cleanup actions here
    print("Cleanup after playbook error")



def blowaway():
    playbook("blowaway.yaml", extra=get_deployment_state_vars())

def base():
    playbook("base.yaml", extra=get_deployment_state_vars())


def prometheus():
    playbook("prometheus.yaml", extra=get_deployment_state_vars())


def scaphandre():
    playbook("scaphandre.yaml", extra=get_deployment_state_vars())


def deploy_k3s():
    playbook("deploy_k3s.yaml", extra=get_deployment_state_vars())


def strimzi():
    playbook("strimzi.yaml",
        extra=get_deployment_state_vars() | factors(),
    )


def theodolite():
    playbook("theodolite.yaml",
        extra=get_deployment_state_vars() | factors(),
    )

def killexp():
    playbook("killexp.yaml",
        extra=get_deployment_state_vars() | factors(),
    )


def exp(exp_name, experiment_description):
    from .g import g

    g.init_exp(exp_name, experiment_description)
    playbook(
        "generate_experiment.yaml",
        extra=get_deployment_state_vars() | get_experiment_state_vars() | factors(),
    )
    playbook(
        "_current_exp.yaml",
        extra=get_deployment_state_vars() | get_experiment_state_vars() | factors(),
    )
    g.end_exp()
