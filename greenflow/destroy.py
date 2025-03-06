#!/usr/bin/env python3
from os import system
from shlex import split
from time import sleep

import ansible_runner
import pendulum

import gin

from .factors import factors
from .g5k import G5KPlatform
from .g5knos import G5KNixOSPlatform
from .platform import MockPlatform, Platform
from .playbook import _playbook


def blowaway():
    _playbook("blowaway.yaml")


def pre_destroy():
    pass
    # g.storage.wrap_up_exp()

    # try:
    #     p = helm(
    #         split("uninstall victoria-metrics-single"),
    #         # _bg=True,
    #     )
    #     p.wait(timeout=10)
    # except:
    #     pass


def post_destroy():
    pass
    # p = ssh(
    #     split(
    #         "h-0 sudo rsync -aXxvPh --exclude '*cache*' --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 /mnt/energystream1/ /root/energystream1-mirror"
    #     ),
    #     _fg=True,
    # )
    # ssh(split("h-0 docker restart greenflow-vm-1"))


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
        case G5KNixOSPlatform():
            pre_destroy()
            p.teardown()
            post_destroy()


@gin.configurable
def killjob(*, platform=gin.REQUIRED):
    p: Platform = platform()
    match p:
        case G5KPlatform():
            p.teardown()
        case G5KNixOSPlatform():
            p.teardown()
