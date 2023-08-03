import gin

from invoke import task
from greenflow import destroy, g, playbook, provision

def load_gin(experiment_name):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
            f"{g.g.gitroot}/gin/{experiment_name}.gin",
        ],
        [],
    )


@task
def setup(c, experiment_name):
    load_gin(experiment_name)
    provision.provision()
    playbook.deploy_k3s()
    playbook.prometheus()
    playbook.scaphandre()
    playbook.strimzi()
    playbook.theodolite()


@task
def exp(c, experiment_name, description=''):
    load_gin(experiment_name)
    playbook.exp(experiment_name=experiment_name, experiment_description=description)


@task
def prometheus(c, experiment_name):
    load_gin(experiment_name)
    playbook.prometheus()

@task
def theo(c, experiment_name):
    load_gin(experiment_name)
    playbook.theodolite()

@task
def scaph(c, experiment_name):
    load_gin(experiment_name)
    playbook.scaphandre()

@task
def killjob(c):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
        ],
        [],
    )
    destroy.killjob()

@task(setup, exp, killjob)
def e2e(c, experiment_name):
    load_gin(experiment_name)

    destroy.killjob()
