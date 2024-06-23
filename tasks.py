import bpdb
from invoke import task
from ptpython import embed

from greenflow import destroy, g, provision
from greenflow.playbook import (
    deploy_k3s,
    p,
    kafka,
    prometheus,
    scaphandre,
    strimzi,
    redpanda,
    redpanda_test,
    kminion,
)

ntfy_url = "https://ntfy.sh/test-greenflow"
import requests

import gin


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
    try:
        provision.provision()
        deploy_k3s()
        p(prometheus)
        p(scaphandre)
        p(strimzi)
        # assert False
        # p(kminion)
        send_notification("Base Setup complete. Dropped into shell")
        embed(globals(), locals())
    except:
        embed(globals(), locals())
        bpdb.post_mortem()
    # playbook.kafka()
    # playbook.redpanda()
    # playbook.theodolite()

    send_notification("Setup complete")



@task
def exp(c, exp_name, description="", load=None, instances=None, workers=None):
    from greenflow.playbook import exp


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
        embed(globals(), locals())
        exp(exp_name=exp_name, experiment_description=description)
    except:
        bpdb.post_mortem()

    send_notification("Experiment complete. On to the next.")


@task
def killjob(c):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
        ],
        [],
    )
    destroy.killjob()


@task
def screen(c):
    from greenflow.screen import ExperimentApp

    TA = ExperimentApp()
    TA.run()
