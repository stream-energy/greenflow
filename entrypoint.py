import traceback
import requests
import gin
from greenflow.adaptive import *
from greenflow.glue import (
    embed,
    ntfy_url,
    patch_global_g,
    setup_gin_config,
    kafka_context,
    redpanda_context,
)
from greenflow.playbook import (
    deploy_k3s,
    p,
    prometheus,
    scaphandre,
    strimzi,
)
from dataclasses import dataclass
from bpdb import set_trace, post_mortem
import click
import kr8s

import logging
from logfmter import Logfmter

datefmt = "%Y.%m.%d.%a.%H-%M-%S"
formatter = Logfmter(
    keys=[
        "ts",
        "lvl",
        "at",
        "lno",
    ],
    mapping={
        "ts": "asctime",
        "lvl": "levelname",
        "at": "pathname",
        "lno": "lineno",
    },
    datefmt=datefmt,
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)


logging.basicConfig(handlers=[handler], level=logging.WARN)


def load_gin(exp_name="ingest-redpanda", test=False):
    if test:
        os.environ["EXPERIMENT_STORAGE_URL"] = os.environ["TEST_EXPERIMENT_STORAGE_URL"]
        os.environ["PROMETHEUS_URL"] = os.environ["TEST_PROMETHEUS_URL"]
        os.environ["EXPERIMENT_PUSHGATEWAY_URL"] = os.environ[
            "TEST_EXPERIMENT_PUSHGATEWAY_URL"
        ]
        os.environ["DASHBOARD_BASE_URL"] = os.environ["TEST_DASHBOARD_BASE_URL"]
        os.environ["NTFY_URL"] = os.environ["TEST_NTFY_URL"]
        g = patch_global_g("test")
        config_files = [
            "test-platform.gin",
            f"{exp_name}.gin",
            "test-platform.gin",
        ]
    else:
        g = patch_global_g("production")
        config_files = [
            "vmon-defaults.gin",
            "g5k/defaults.gin",
            # "g5k/paravance.gin",
            # "g5k/parasilo.gin",
            # "g5k/montcalm.gin",
            # "g5k/chirop.gin",
            "g5k/neowise.gin",
            f"{exp_name}.gin",
        ]

    setup_gin_config(g, exp_name, config_files)


def rebind_parameters(**kwargs):
    parameter_mapping = {
        "load": "greenflow.factors.exp_params.load",
        "instances": "greenflow.factors.exp_params.instances",
        "messageSize": "greenflow.factors.exp_params.messageSize",
        "partitions": "greenflow.factors.exp_params.partitions",
        "bootstrap_servers": "greenflow.factors.kafka_bootstrap_servers",
        "redpanda_write_caching": "greenflow.factors.exp_params.redpanda_write_caching",
        "durationSeconds": "greenflow.factors.exp_params.durationSeconds",
        "brokerCpu": "greenflow.factors.exp_params.broker_cpu",
        "brokerMem": "greenflow.factors.exp_params.broker_mem",
    }

    with gin.unlock_config():
        for key, value in kwargs.items():
            if value is not None and key in parameter_mapping:
                gin.bind_parameter(parameter_mapping[key], value)


@click.command("ingest")
# @click.argument("exp_name", type=str, default="ingest-redpanda")
@click.argument("exp_description", type=str)
@click.option("--load", type=str)
@click.option("--messageSize", type=int)
@click.option("--instances", type=int)
@click.option("--partitions", type=int)
def ingest_set(exp_description, **kwargs):
    from greenflow.playbook import exp
    from greenflow.adaptive import threshold_hammer

    # load_gin(exp_name)

    messageSizes = [
        128,
        512,
    ] + list(range(1024, 10241, 1024))
    try:
        exp_name = "ingest-kafka"
        with kafka_context():
            load_gin(exp_name)
            threshold_hammer(exp_description, messageSizes)
        exp_name = "ingest-redpanda"
        with redpanda_context():
            load_gin(exp_name)
            threshold_hammer(exp_description, messageSizes)
    except:
        send_notification("Error in experiment. Debugging with shell")
        traceback.print_exc()
        post_mortem()

    send_notification("Experiment complete. On to the next.")


@click.command("setup")
@click.argument("exp_name", type=str, default="ingest-redpanda")
@click.option("--workers", type=int)
def setup(exp_name, workers):
    load_gin(exp_name=exp_name)

    from greenflow import provision

    if workers is not None:
        with gin.unlock_config():
            gin.bind_parameter(
                "greenflow.g5k.G5KPlatform.get_conf.num_worker", int(workers)
            )
    try:
        # provision.provision()
        deploy_k3s()
        p(prometheus)
        p(scaphandre)
        p(strimzi)
        # # Warm-up Kafka and Redpanda in the first time setup
        with kafka_context():
            pass
        with redpanda_context():
            pass
    except:
        send_notification("Error in setup. Dropped into shell")
        post_mortem()

    send_notification("Setup complete")


@click.command("test")
@click.argument("exp_name", type=str, default="ingest-redpanda")
def test(exp_name: str):
    load_gin(exp_name=exp_name, test=True)

    from greenflow.exp_ng.exp_ng import exp as exp, killexp
    from greenflow.exp_ng.hammer import hammer
    from greenflow import provision

    logging.warning({"exp_name": exp_name})
    # provision.provision()
    # deploy_k3s()
    # p(
    # p(prometheus)
    # p(strimzi)
    # with redpanda_context():
    #     ...
    # with kafka_context():
    #     ...
    # p(kafka)
    # p(redpanda)
    rebind_parameters(
        load=5.0 * 10**3,
        messageSize=1024,
        durationSeconds=100,
    )
    # hammer()
    messageSizes = [
        128,
        512,
    ] + list(range(1024, 10241, 1024))
    threshold_hammer("test", messageSizes)


@click.command("killjob")
def killjob():
    load_gin()

    from greenflow import destroy

    destroy.killjob()


@click.command("kexp")
@click.argument("exp_name", type=str, default="ingest-redpanda")
def kexp(exp_name: str):
    load_gin(exp_name=exp_name)

    from greenflow.exp_ng.exp_ng import killexp

    killexp()


@click.command("tkexp")
@click.argument("exp_name", type=str, default="ingest-redpanda")
def tkexp(exp_name: str):
    load_gin(exp_name=exp_name, test=True)
    from greenflow.exp_ng.exp_ng import killexp

    killexp()


def send_notification(text, priority="low"):
    requests.post(ntfy_url, headers={"priority": priority}, data=text, timeout=10)


@click.command("i")
@click.argument("exp_name", type=str, default="ingest-redpanda")
@click.option("--load", type=str)
@click.option("--messageSize", type=int)
@click.option("--instances", type=int)
@click.option("--partitions", type=int)
def i(exp_name, **kwargs):
    load_gin(exp_name)
    rebind_parameters(**kwargs)
    embed(globals(), locals())


@click.group()
def cli():
    pass


cli.add_command(setup)
cli.add_command(ingest_set)
cli.add_command(i)
cli.add_command(killjob)
cli.add_command(tkexp)
cli.add_command(kexp)
cli.add_command(test)


if __name__ == "__main__":
    cli()
