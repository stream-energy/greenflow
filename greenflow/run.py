#!/usr/bin/env python3
import json
from shlex import split

import ansible_runner
import gin
import pendulum
from sh import ansible_playbook, rm

from .factors import factors

from .g import g
from .g5k import G5KPlatform
from .platform import MockPlatform, Platform


def pre_setup():
    # g.storage.create_new_exp()
    g.storage.create_new_exp()


def post_setup():
    pass


def exp():
    gin.parse_config_file("params/exp.gin")
    run = ansible_runner.run(
        # role="helm",
        # inventory=p.ansible_inventory_file_path,
        playbook="exp.yaml",
        private_data_dir="./ansible",
        # TODO: Rename all instances of deployment_ts to deployment_start_ts
        extravars={"deployment_start_ts": g.deployment_start.to_iso8601_string()}
        | factors(),
        # rotate_artifacts=5,
    )
    # run = ansible_runner.run(
    #     # role="helm",
    #     # inventory=p.ansible_inventory_file_path,
    #     playbook="base.yaml",
    #     private_data_dir="./ansible",
    #     # TODO: Rename all instances of deployment_ts to deployment_start_ts
    #     extravars={"deployment_start_ts": g.deployment_start.to_iso8601_string()},
    #     # rotate_artifacts=5,
    # )

    # run.get_fact_cache("nova-1.lyon.grid5000.fr")
    # ansible_playbook(
    #     split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
    # )


def base():
    run = ansible_runner.run(
        # role="helm",
        # inventory=p.ansible_inventory_file_path,
        playbook="base.yaml",
        private_data_dir="./ansible",
        # TODO: Rename all instances of deployment_ts to deployment_start_ts
        extravars={"deployment_start_ts": g.deployment_start.to_iso8601_string()}
        | factors(),
        # rotate_artifacts=5,
    )
    # gin.parse_config_file("params/exp.gin")
    # run = ansible_runner.run(
    #     # role="helm",
    #     # inventory=p.ansible_inventory_file_path,
    #     playbook="exp.yaml",
    #     private_data_dir="./ansible",
    #     # TODO: Rename all instances of deployment_ts to deployment_start_ts
    #     extravars={"deployment_start_ts": g.deployment_start.to_iso8601_string()}
    #     | factors(),
    #     # rotate_artifacts=5,
    # )
    # run = ansible_runner.run(
    #     # role="helm",
    #     # inventory=p.ansible_inventory_file_path,
    #     playbook="base.yaml",
    #     private_data_dir="./ansible",
    #     # TODO: Rename all instances of deployment_ts to deployment_start_ts
    #     extravars={"deployment_start_ts": g.deployment_start.to_iso8601_string()},
    #     # rotate_artifacts=5,
    # )

    # run.get_fact_cache("nova-1.lyon.grid5000.fr")
    # ansible_playbook(
    #     split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
    # )


def theo():
    run = ansible_runner.run(
        # role="helm",
        # inventory=p.ansible_inventory_file_path,
        playbook="theo.yaml",
        private_data_dir="./ansible",
        # TODO: Rename all instances of deployment_ts to deployment_start_ts
        extravars={
            "deployment_start_ts": g.deployment_start.to_iso8601_string(),
        }
        | factors(),
        # rotate_artifacts=5,
    )


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
        }
        | factors(),
        # rotate_artifacts=5,
    )

    # run.get_fact_cache("nova-1.lyon.grid5000.fr")
    # ansible_playbook(
    #     split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
    # )


if __name__ == "__main__":
    run()
