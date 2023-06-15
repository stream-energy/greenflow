#!/usr/bin/env python3

import gin
import yaml

from .g5k import G5KPlatform
from .platform import MockPlatform, Platform


def post_setup():
    pass


@gin.configurable
def provision(*, platform: type[Platform] = gin.REQUIRED):
    p: Platform = platform()

    p.pre_provision()

    p.provision()

    p.post_provision()

    match p:
        case MockPlatform():
            pass
        case G5KPlatform():
            with open("./ansible/inventory/hosts.yaml", "w") as f:
                yaml.dump(p.get_ansible_inventory(), f)


if __name__ == "__main__":
    provision()
