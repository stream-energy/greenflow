#!/usr/bin/env python3
from shlex import split

import ansible_runner
import gin
from sh import ansible_playbook
import pendulum

from .g5k import G5KPlatform
from .platform import Platform

from . import g


def pre_deploy(platform: Platform):
    # g.storage.create_new_exp()
    g.storage.create_new_exp()
    g.storage.write_gin_config()
    platform.pre_deploy()


def post_deploy(platform: Platform):
    # g.storage.create_new_exp()
    platform.post_deploy()
    # g.storage.


@gin.configurable
def deploy(*, platform: type[Platform] = gin.REQUIRED):
    p: Platform = platform()
    g.deployment_start = pendulum.now()
    match p:
        case G5KPlatform():
            pre_deploy(p)
            inv = p.deploy()
            post_deploy(p)

            ansible_runner.run(
                playbook="k3s-setup.yaml",
                inventory=p.ansible_inventory_file_path,
                private_data_dir=".",
            )
            # ansible_runner.run(
            #     playbook="helm-setup.yaml",
            #     inventory=p.ansible_inventory_file_path,
            #     private_data_dir=".",
            #     tags=["redeploy"]
            #     # cmdline=["-t", "redeploy"],
            # )
            # TODO: Convert to ansible runner in order to be able to pass in vars
            # ansible_playbook(
            #     split(
            #         f"helm-setup.yaml -i {p.ansible_inventory_file_path} -t redeploy"
            #     ),
            #     _fg=True,
            # )
            # run = ansible_runner.run(
            #     playbook="helm-setup.yaml",
            #     inventory=p.ansible_inventory_file_path,
            #     private_data_dir=".",
            #     extravars={"deployment_ts": g.deployment_start.to_iso8601_string()},
            #     rotate_artifacts=5,
            # )
            run = ansible_runner.run(
                role="helm",
                inventory=p.ansible_inventory_file_path,
                private_data_dir=".",
                extravars={"deployment_ts": g.deployment_start.to_iso8601_string()},
                rotate_artifacts=5,
            )

            run.get_fact_cache("nova-1.lyon.grid5000.fr")
            # TODO: Convert to ansible runner in order to be able to pass in vars
            # ansible_playbook(
            #     split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
            # )


if __name__ == "__main__":
    deploy()
