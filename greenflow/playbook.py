#!/usr/bin/env python3

from sys import exit
import ansible_runner

from .factors import factors
from .state import get_deployment_state_vars, get_experiment_state_vars
from .g import g

# extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()


def playbook(playbook_name, extra=None):
    extra = extra or {}
    rc = ansible_runner.run(
        playbook=playbook_name,
        private_data_dir=f"{g.gitroot}/ansible",
        extravars=extra,
    ).rc
    if rc > 0:
        exit("Error: Playbook execution interrupted/failed.")


def blowaway():
    playbook("blowaway.yaml", get_deployment_state_vars())


def base():
    playbook("base.yaml", get_deployment_state_vars())


def prometheus():
    playbook("prometheus.yaml", get_deployment_state_vars())


def scaphandre():
    playbook("scaphandre.yaml", get_deployment_state_vars())


def deploy_k3s():
    playbook("deploy_k3s.yaml", get_deployment_state_vars())


def run_playbook(playbook_name):
    extra_vars = get_deployment_state_vars() | factors()
    playbook(playbook_name, extra_vars)


def exp(exp_name, experiment_description):
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    g.init_exp(exp_name, experiment_description)
    playbook("generate_experiment.yaml", extra_vars)
    playbook("_current_exp.yaml", extra_vars)
    g.end_exp()


def strimzi():
    run_playbook("strimzi.yaml")


def kafka():
    run_playbook("kafka.yaml")


def theodolite():
    run_playbook("theodolite.yaml")

def kminion():
    run_playbook("kminion.yaml")

def redpanda():
    run_playbook("redpanda.yaml")


# for playbook_name in [
#     "redpanda.yaml",
#     "kafka.yaml",
#     "theodolite.yaml",
#     "killexp.yaml",
#     "redpanda_test.yaml",
# ]:
#     globals()[playbook_name.split(".")[0]] = lambda: run_playbook(playbook_name)
