#!/usr/bin/env python3
from shlex import split
from time import sleep

import gin
from sh import kubectl, ssh

from .g5k import G5KPlatform
from .platform import Platform


def pre_destroy():
    try:
        p = kubectl(
            split("delete -n monitoring statefulsets victoria-metrics-single-server"),
            _bg=True,
        )
        p.wait(timeout=2)
    except:
        pass
    sleep(5)


def post_destroy():
    ssh(
        split(
            "h-0 sudo rsync -aXxvPh --exclude '*cache*' --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 lyon.grid5000.fr:/home/***REMOVED***/k8s /root/"
        )
    )
    ssh(split("h-0 docker restart vm"))


@gin.configurable
def destroy(*, platform=gin.REQUIRED):
    p: Platform = platform()
    match p:
        case G5KPlatform():
            pre_destroy()
            p.destroy()
            post_destroy()


if __name__ == "__main__":
    destroy()
