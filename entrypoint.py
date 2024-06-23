import requests
import gin
from greenflow import destroy, g, playbook, provision, factors
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
from dataclasses import dataclass
from bpdb import set_trace, post_mortem
from ptpython.repl import embed
from sh import kubectl, helm

# from bpython.cli import main as oldbpython
import click
from shlex import split

ntfy_url = "https://ntfy.sh/4d5a7713-8b2a-46c8-8407-0014b19aa54a-greenflow"


def load_gin(exp_name="ingest-kafka"):
    with gin.unlock_config():
        gin.parse_config_files_and_bindings(
            [
                f"{g.g.gitroot}/gin/vmon-defaults.gin",
                f"{g.g.gitroot}/gin/g5k/defaults.gin",
                f"{g.g.gitroot}/gin/g5k/paravance.gin",
                f"{g.g.gitroot}/gin/{exp_name}.gin",
            ],
            [],
        )


def rebind_parameters(**kwargs):
    parameter_mapping = {
        "load": "greenflow.factors.exp_params.load",
        "instances": "greenflow.factors.exp_params.instances",
        "message_size": "greenflow.factors.exp_params.messageSize",
        "bootstrap_servers": "greenflow.factors.kafka_bootstrap_servers",
        "redpanda_write_caching": "greenflow.factors.exp_params.redpanda_write_caching",
    }

    with gin.unlock_config():
        for key, value in kwargs.items():
            if value is not None and key in parameter_mapping:
                gin.bind_parameter(parameter_mapping[key], value)


def send_notification(text, priority="low"):
    requests.post(ntfy_url, headers={"priority": priority}, data=text, timeout=10)


def test_message_delivery():
    send_notification("Test message")


@click.command("test")
@click.argument("exp_name", type=str)
@click.option("--workers", type=int)
def test(exp_name, workers):
    load_gin(exp_name)
    if workers is not None:
        with gin.unlock_config():
            gin.bind_parameter(
                "greenflow.g5k.G5KPlatform.get_conf.num_worker", int(workers)
            )
    try:
        p(prometheus)
        p(scaphandre)
        p(strimzi)
        # # Warm-up Kafka and Redpanda in the first time setup
        p(kafka)
        kubectl(split("delete kafka theodolite-kafka"))
        helm(split("uninstall kminion"))
        p(redpanda)
        helm(split("uninstall -n redpanda redpanda"))
        helm(split("uninstall -n redpanda kminion"))
        send_notification("Base Setup complete. Dropped into shell")
        embed(globals(), locals())
    except:
        send_notification("Error in setup. Dropped into shell")
        post_mortem()
        # embed(globals(), locals())
    # playbook.kafka()
    # playbook.redpanda()
    # playbook.theodolite()

    send_notification("Setup complete")

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
        p(kafka)
        kubectl(split("delete kafka theodolite-kafka"))
        helm(split("uninstall kminion"))
        p(redpanda)
        helm(split("uninstall -n redpanda redpanda"))
        helm(split("uninstall -n redpanda kminion"))
        send_notification("Base Setup complete. Dropped into shell")
        embed(globals(), locals())
    except:
        send_notification("Error in setup. Dropped into shell")
        embed(globals(), locals())
    # playbook.kafka()
    # playbook.redpanda()
    # playbook.theodolite()

    send_notification("Setup complete")


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


@click.command("ingest")
@click.argument("exp_name", type=str, default="ingest-redpanda")
@click.option("--load", type=str)
@click.option("--message_size", type=int)
@click.option("--instances", type=int)
@click.option("--partitions", type=int)
def ingest(exp_name, **kwargs):
    from greenflow.playbook import exp

    instances = 2
    try:
        load_gin(exp_name)
        rebind_parameters(redpanda_write_caching=False)
        p(redpanda)
        exp(exp_name=exp_name, experiment_description="Warmup")
        for message_size in [64]:
            for load in range(500000, 1000000, 50000):
                rebind_parameters(load=load, message_size=message_size)
                exp(exp_name=exp_name, experiment_description="")
        helm(split("uninstall -n redpanda redpanda"))
        helm(split("uninstall -n redpanda kminion"))

        exp_name = "ingest-redpanda"
        load_gin(exp_name)
        rebind_parameters(redpanda_write_caching=True)
        p(redpanda)
        exp(exp_name=exp_name, experiment_description="Warmup")
        for message_size in [64]:
            for load in range(500000, 1000000, 50000):
                rebind_parameters(load=load, message_size=message_size)
                exp(exp_name=exp_name, experiment_description="")
        helm(split("uninstall -n redpanda redpanda"))
        helm(split("uninstall -n redpanda kminion"))
    except:
        send_notification("Error in experiment. Debugging with shell")
        pdb.post_mortem()

    send_notification("Experiment complete. On to the next.")


@click.command("killjob")
def killjob():
    load_gin()
    destroy.killjob()


@click.group()
def cli():
    pass


cli.add_command(setup)
cli.add_command(ingest)
cli.add_command(i)
cli.add_command(test)
cli.add_command(killjob)

if __name__ == "__main__":
    cli()
