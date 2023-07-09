from invoke import task

import gin
from greenflow import destroy, g, playbook, provision


def load_gin(file_name_without_gin_extension):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
            f"{g.g.gitroot}/gin/{file_name_without_gin_extension}.gin",
        ],
        [],
    )


@task
def setup(c, file_name_without_gin_extension):
    load_gin(file_name_without_gin_extension)
    provision.provision()
    playbook.deploy_k3s()
    playbook.prometheus()
    playbook.scaphandre()
    playbook.strimzi()
    playbook.theodolite()


@task
def exp(c, file_name_without_gin_extension):
    load_gin(file_name_without_gin_extension)
    playbook.exp()


@task
def prometheus(c, file_name_without_gin_extension):
    load_gin(file_name_without_gin_extension)
    playbook.prometheus()

@task
def theo(c, file_name_without_gin_extension):
    load_gin(file_name_without_gin_extension)
    playbook.theodolite()

@task
def scaph(c, file_name_without_gin_extension):
    load_gin(file_name_without_gin_extension)
    playbook.scaphandre()

@task
def e2e(c, file_name_without_gin_extension):
    load_gin(file_name_without_gin_extension)
    provision.provision()
    playbook.deploy_k3s()
    playbook.prometheus()
    playbook.scaphandre()
    playbook.strimzi()
    playbook.theodolite()

    playbook.exp()

    destroy.killjob()


@task
def killjob(c):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
        ],
        [],
    )
    destroy.killjob()
