#!/usr/bin/env python3
from shlex import split

import ansible_runner
import gin
from sh import ansible_playbook

from .g5k import G5KPlatform
from .platform import Platform


@gin.configurable
def deploy(*, platform: type[Platform] = gin.REQUIRED):
    p: Platform = platform()
    match p:
        case G5KPlatform():
            p.pre_deploy()
            p.deploy()
            p.post_deploy()

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
            ansible_playbook(
                split(
                    f"helm-setup.yaml -i {p.ansible_inventory_file_path} -t redeploy"
                ),
                _fg=True,
            )
            # ansible_runner.run(
            #     playbook="helm-setup.yaml",
            #     inventory=p.ansible_inventory_file_path,
            #     private_data_dir=".",
            #     # cmdline=["-t", "redeploy"],
            # )
            # TODO: Convert to ansible runner in order to be able to pass in vars
            ansible_playbook(
                split(f"helm-setup.yaml -i {p.ansible_inventory_file_path}"), _fg=True
            )


if __name__ == "__main__":
    deploy()
