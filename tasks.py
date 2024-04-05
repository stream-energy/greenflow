import pdb
from invoke import task

ntfy_url = "https://ntfy.sh/test-greenflow"
import requests

import gin
from greenflow import destroy, g, playbook, provision


def load_gin(exp_name):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/vmon-defaults.gin",
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
            f"{g.g.gitroot}/gin/{exp_name}.gin",
        ],
        [],
    )


def send_notification(text):
    ntfy_url = "https://ntfy.sh/4d5a7713-8b2a-46c8-8407-0014b19aa54a-greenflow"
    requests.post(ntfy_url, headers={"priority": "low"}, data=text)


@task
def test_message_delivery(c):
    send_notification("Test message")


@task
def setup(c, exp_name, workers=None):
    load_gin(exp_name)
    if workers is not None:
        with gin.unlock_config():
            gin.bind_parameter(
                "greenflow.g5k.G5KPlatform.get_conf.num_worker", int(workers)
            )
    provision.provision()
    playbook.deploy_k3s()
    playbook.prometheus()
    playbook.scaphandre()
    playbook.strimzi()
    playbook.kafka()
    playbook.redpanda()
    playbook.theodolite()

    send_notification("Setup complete")


@task
def exp(c, exp_name, description="", load=None, instances=None, workers=None):
    load_gin(exp_name)
    if load is not None:
        with gin.unlock_config():
            gin.bind_parameter("greenflow.factors.exp_params.load", load)
    if workers is not None:
        with gin.unlock_config():
            gin.bind_parameter("greenflow.g5k.G5KPlatform.get_conf.num_worker", workers)
    if instances is not None:
        with gin.unlock_config():
            gin.bind_parameter("greenflow.factors.exp_params.instances", instances)
    try:
        playbook.exp(exp_name=exp_name, experiment_description=description)
    except:
        pdb.post_mortem()

    send_notification("Experiment complete. On to the next.")


@task
def prometheus(c, exp_name):
    load_gin(exp_name)
    playbook.prometheus()


@task
def theo(c):
    load_gin("uc3-flink-kafka")
    playbook.theodolite()


@task
def scaph(c, exp_name):
    load_gin(exp_name)
    playbook.scaphandre()


@task
def strimzi(c, exp_name="ingest-kafka"):
    load_gin(exp_name)
    playbook.strimzi()

@task
def kafka(c, exp_name="ingest-kafka"):
    load_gin(exp_name)
    playbook.kafka()

@task
def redpanda(c, exp_name="ingest-redpanda"):
    load_gin(exp_name)
    playbook.redpanda()


@task
def blowaway(c, exp_name):
    load_gin(exp_name)
    playbook.blowaway()


@task
def killexp(c, exp_name):
    load_gin(exp_name)
    playbook.killexp()


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
def e2e(c, exp_name):
    load_gin(exp_name)

    destroy.killjob()


@task
def screen(c):
    from greenflow.screen import ExperimentApp

    TA = ExperimentApp()
    TA.run()
