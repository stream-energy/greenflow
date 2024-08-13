import requests
import gin
from greenflow import destroy, g, provision
from greenflow.adaptive import *
from greenflow.playbook import (
    deploy_k3s,
    p,
    kafka,
    prometheus,
    scaphandre,
    strimzi,
    redpanda,
)
from dataclasses import dataclass
from bpdb import set_trace, post_mortem
from sh import kubectl, helm
import click
from shlex import split
from contextlib import contextmanager

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


logging.basicConfig(handlers=[handler], level=logging.INFO)


def embed(globals, locals):
    from ptpython.repl import embed
    from os import getenv

    embed(
        history_filename=f"{getenv('DEVENV_ROOT')}/.devenv/.ptpython-history",
        globals=globals,
        locals=locals,
    )


# Configure NTFY_URL in .secrets.env to get notifications on your phone!
# Once the experiment is complete or if there is an error, you will get a notification
ntfy_url = os.getenv("NTFY_URL", "http://ntfy.sh/YOUR_URL_HERE")


def load_gin(exp_name="ingest-kafka"):
    with gin.unlock_config():
        gin.parse_config_files_and_bindings(
            [
                f"{g.g.gitroot}/gin/vmon-defaults.gin",
                f"{g.g.gitroot}/gin/g5k/defaults.gin",
                # f"{g.g.gitroot}/gin/g5k/paravance.gin",
                # f"{g.g.gitroot}/gin/g5k/parasilo.gin",
                # f"{g.g.gitroot}/gin/g5k/montcalm.gin",
                f"{g.g.gitroot}/gin/g5k/chirop.gin",
                # f"{g.g.gitroot}/gin/g5k/neowise.gin",
                f"{g.g.gitroot}/gin/{exp_name}.gin",
            ],
            [],
        )


def rebind_parameters(**kwargs):
    parameter_mapping = {
        "load": "greenflow.factors.exp_params.load",
        "instances": "greenflow.factors.exp_params.instances",
        "message_size": "greenflow.factors.exp_params.messageSize",
        "partitions": "greenflow.factors.exp_params.partitions",
        "bootstrap_servers": "greenflow.factors.kafka_bootstrap_servers",
        "redpanda_write_caching": "greenflow.factors.exp_params.redpanda_write_caching",
        "durationSeconds": "greenflow.factors.exp_params.durationSeconds",
    }

    with gin.unlock_config():
        for key, value in kwargs.items():
            if value is not None and key in parameter_mapping:
                gin.bind_parameter(parameter_mapping[key], value)


# Context manager for kafka setup and teardown
@contextmanager
def kafka_context():
    load_gin("ingest-kafka")
    p(kafka)
    yield
    kubectl(split("delete kafka theodolite-kafka"))
    helm(split("uninstall -n default kminion"))


@contextmanager
def redpanda_context():
    load_gin("ingest-redpanda")
    p(redpanda)
    yield
    helm(split("uninstall -n redpanda redpanda"))
    helm(split("uninstall -n redpanda kminion"))


@click.command("setup")
@click.argument("exp_name", type=str)
@click.option("--workers", type=int)
def setup(exp_name, workers):
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
        # # Warm-up Kafka and Redpanda in the first time setup
        with kafka_context():
            pass
        with redpanda_context():
            pass
    except:
        send_notification("Error in setup. Dropped into shell")
        post_mortem()

    send_notification("Setup complete")


def generate_experiment_pairs():
    experiment_pairs = []

    # For 512 bytes
    for load in [50000, 100000, 250000, 500000, 1000000, 2000000, 3000000]:
        experiment_pairs.append((load, 512))

    # For 1024 bytes
    for load in [50000, 100000, 250000, 500000, 750000, 1000000]:
        experiment_pairs.append((load, 1024))

    # For 2048 bytes
    for load in [50000, 100000, 250000, 400000, 550000, 700000]:
        experiment_pairs.append((load, 2048))

    # For 4096 bytes
    for load in [50000, 75000, 100000, 125000]:
        experiment_pairs.append((load, 4096))

    # For 6144 bytes
    for load in [25000, 50000, 75000]:
        experiment_pairs.append((load, 6144))

    # For 8192 bytes
    for load in [25000, 40000, 55000]:
        experiment_pairs.append((load, 8192))

    # For 10240 bytes
    for load in [25000, 35000, 45000]:
        experiment_pairs.append((load, 10240))

    return experiment_pairs

def search_space(experiment_pairs: list[tuple[int, int]], exp_name: str, exp_description: str) -> list[dict]:
    results = []
    from greenflow.playbook import exp

    for load, message_size in experiment_pairs:
        rebind_parameters(load=load, message_size=message_size)
        # exp is calling ansible_runner
        # Its output is very verbose, so we are not printing it
        # Suppress stdout and stderr before calling exp
        with open("/tmp/greenflow.log", "a+") as f, contextlib.redirect_stdout(
            f
        ), contextlib.redirect_stderr(f):
            exp(
                exp_name=exp_name,
                experiment_description=exp_description,
            )
            logging.info(dict(msg="Completed", load=load, message_size=message_size))

    return results


@click.command("ingest")
@click.argument("exp_name", type=str, default="ingest-redpanda")
@click.option("--load", type=str)
@click.option("--message_size", type=int)
@click.option("--instances", type=int)
@click.option("--partitions", type=int)
def ingest(exp_name, **kwargs):
    from greenflow.playbook import exp

    exp_description = "cluster=chirop type=search-space"

    message_sizes = [
        128,
        512,
    ] + list(range(1024, 10241, 1024))
    try:
        # with kafka_context():

        #     logging.info(threshold("ingest-kafka", exp_description, message_sizes))
        with redpanda_context():
            experiment_pairs = generate_experiment_pairs()
            results = search_space(
                experiment_pairs,
                exp_name="ingest-redpanda",
                exp_description=exp_description
            )
            # logging.info(threshold("ingest-redpanda", exp_description, message_sizes))
    except:
        send_notification("Error in experiment. Debugging with shell")
        post_mortem()

    send_notification("Experiment complete. On to the next.")

@click.command("killjob")
def killjob():
    load_gin()
    destroy.killjob()


def send_notification(text, priority="low"):
    requests.post(ntfy_url, headers={"priority": priority}, data=text, timeout=10)


@click.command("i")
@click.argument("exp_name", type=str, default="ingest-redpanda")
@click.option("--load", type=str)
@click.option("--message_size", type=int)
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
cli.add_command(ingest)
cli.add_command(i)
cli.add_command(killjob)


if __name__ == "__main__":
    cli()
