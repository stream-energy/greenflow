from contextlib import contextmanager
from shlex import split
import gin
from sh import helm, kubectl
from greenflow.adaptive import os
import greenflow.g
from greenflow.playbook import kafka, p, redpanda


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


def patch_global_g(deployment_type, storage_type="mongo"):
    import greenflow.g
    from greenflow.g import _g
    import gin

    with gin.unlock_config():
        gin.bind_parameter("greenflow.g._g.deployment_type", deployment_type)
        gin.bind_parameter("greenflow.g._g.storage_type", storage_type)
    g = _g.get_g()
    try:
        _ = greenflow.g.g
    except AttributeError:
        greenflow.g.g = g
    from greenflow import provision, destroy

    return g


def setup_gin_config(g, exp_name, config_files):
    import gin

    with gin.unlock_config():
        gin.parse_config_files_and_bindings(
            [f"{g.gitroot}/gin/{file}" for file in config_files],
            [],
        )


@contextmanager
def kafka_context():
    # from entrypoint import load_gin
    # load_gin("ingest-kafka")
    p(kafka)
    yield
    kubectl(split("delete kafka theodolite-kafka"))
    helm(split("uninstall -n default kminion"))


@contextmanager
def redpanda_context():

    # from entrypoint import load_gin
    # load_gin("ingest-redpanda")
    p(redpanda)
    yield
    helm(split("uninstall -n redpanda redpanda"))
    helm(split("uninstall -n redpanda kminion"))
    kubectl(split("delete -n redpanda pvc --all"))
