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


def pre_setup():
    # g.storage.create_new_exp()
    g.storage.create_new_exp()


def post_setup():
    pass


def run():
    run = ansible_runner.run(
        # role="helm",
        # inventory=p.ansible_inventory_file_path,
        playbook="base.yaml",
        private_data_dir="./ansible",
        # TODO: Rename all instances of deployment_ts to deployment_start_ts
        extravars={"deployment_start_ts": g.deployment_start.to_iso8601_string()},
        # rotate_artifacts=5,
    )

    # run.get_fact_cache("nova-1.lyon.grid5000.fr")
    # ansible_playbook(
    #     split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
    # )


def mrun():
    run = ansible_runner.run(
        # role="helm",
        # inventory=p.ansible_inventory_file_path,
        playbook="base.yaml",
        private_data_dir="./ansible",
        # TODO: Rename all instances of deployment_ts to deployment_start_ts
        extravars={
            "deployment_start_ts": g.deployment_start.to_iso8601_string(),
            "mock": True,
        },
        # rotate_artifacts=5,
    )

    # run.get_fact_cache("nova-1.lyon.grid5000.fr")
    # ansible_playbook(
    #     split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
    # )


if __name__ == "__main__":
    run()
