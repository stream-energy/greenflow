#!/usr/bin/env python3
from os import system
from shlex import split
from time import sleep

import gin
from sh import kubectl, ssh, helm

from .g5k import G5KPlatform
from .platform import Platform
from .g import g
import ansible_runner
import gin
import pendulum
from sh import ansible_playbook, rm

from .factors import factors

from .g import g
from .g5k import G5KPlatform
from .platform import MockPlatform, Platform


def blowaway():
    run = ansible_runner.run(
        # role="helm",
        # inventory=p.ansible_inventory_file_path,
        # verbosity=3,
        playbook="blowaway.yaml",
        private_data_dir="./ansible",
        # TODO: Rename all instances of deployment_ts to deployment_start_ts
        extravars={
            "deployment_start_ts": g.deployment_start.to_iso8601_string(),
        }
        | factors(),
        # rotate_artifacts=5,
    )


def pre_destroy():
    g.storage.wrap_up_exp()

    try:
        p = helm(
            split("uninstall victoria-metrics-single"),
            # _bg=True,
        )
        p.wait(timeout=10)
    except:
        pass


def post_destroy():
    p = ssh(
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


@gin.configurable
def killjob(*, platform=gin.REQUIRED):
    p: Platform = platform()
    # pre_destroy()
    # p.teardown()
    # post_destroy()
    match p:
        case G5KPlatform():
            p.teardown()


def mock_destroy():
    pre_destroy()
    post_destroy()
