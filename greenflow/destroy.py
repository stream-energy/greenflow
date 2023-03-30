#!/usr/bin/env python3
from os import system
from shlex import split
from time import sleep

import gin
from sh import kubectl, ssh

from .g5k import G5KPlatform
from .platform import Platform
from .g import g


def pre_destroy():
    g.storage.wrap_up_exp()

    # p = kubectl(
    #     "port-forward -n monitoring svc/victoria-metrics-single-server 8428:8429".split(
    #         " "
    #     ),
    #     _bg=True,
    # )
    try:
        p = kubectl(
            split(
                "delete --wait=true --timeout=10s statefulsets victoria-metrics-single-server"
            ),
            # _bg=True,
        )
        p.wait(timeout=10)
    except:
        pass


def post_destroy():
    ssh(
        split(
            "h-0 sudo rsync -aXxvPh --exclude '*cache*' --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 /mnt/energystream1/ /root/energystream1-mirror"
        ),
        _fg=True,
    )
    ssh(split("h-0 docker restart greenflow-vm-1"))


@gin.configurable
def destroy(*, platform=gin.REQUIRED):
    p: Platform = platform()
    # pre_destroy()
    # p.teardown()
    # post_destroy()
    match p:
        case G5KPlatform():
            pre_destroy()
            p.teardown()
            post_destroy()


if __name__ == "__main__":
    destroy()
