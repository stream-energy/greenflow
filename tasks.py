from invoke import task
ntfy_url = "https://ntfy.govind.cloud/test"
import requests

import gin
from greenflow import destroy, g, playbook, provision


def load_gin(exp_name):
    gin.parse_config_files_and_bindings(
        [
            f"{g.g.gitroot}/gin/g5k-defaults.gin",
            f"{g.g.gitroot}/gin/{exp_name}.gin",
        ],
        []
    )


@task
def setup(c, exp_name, workers=None):
    load_gin(exp_name)
    if workers is not None:
        with gin.unlock_config():
            gin.bind_parameter("greenflow.g5k.G5KPlatform.get_conf.num_worker", int(workers))
    provision.provision()
    playbook.deploy_k3s()
    playbook.prometheus()
    playbook.scaphandre()
    playbook.strimzi()
    playbook.theodolite()

    requests.post(ntfy_url, data="Setup complete")


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
    playbook.exp(exp_name=exp_name, experiment_description=description)
    requests.post(ntfy_url, data="Experiment complete")


@task
def prometheus(c, exp_name):
    load_gin(exp_name)
    playbook.prometheus()


@task
def theo(c, exp_name):
    load_gin(exp_name)
    playbook.theodolite()


@task
def scaph(c, exp_name):
    load_gin(exp_name)
    playbook.scaphandre()

@task
def kafka(c, exp_name):
    load_gin(exp_name)
    playbook.strimzi()

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

@task()
def csv(c):
    import yaml
    import csv
    import pyperclip
    import io

    with open(f"{g.g.gitroot}/storage/experiment-history.yaml", 'r') as file:
        data = yaml.safe_load(file)

    # Prepare data for csv
    csv_data = []

    # Define the header
    header = [
        "experiment_id",
        "exp_name",
        "dashboard_url",
        "control_hosts",
        "worker_hosts",
        # "job_id",
        # "job_site",
        # "job_started_ts",
        # "deployment_type",
        # "exp_params_duration",
        "exp_params_instances",
        "exp_params_kafkaOnWorker",
        "exp_params_load",
        # "exp_params_warmup",
        # "started_ts",
        # "stopped_ts"
    ]
    csv_data.append(header)

    # Process the YAML data and add to the csv_data
    for key, value in data["_default"].items():
        row = []
        row.append(key)
        row.append(value['exp_name'])
        row.append(value['experiment_metadata']['dashboard_url'])

        # Extract host details
        control_hosts = len(value['experiment_metadata']['deployment_metadata']['ansible_inventory']['all']['children']['control']['hosts'].keys())
        worker_hosts = len(value['experiment_metadata']['deployment_metadata']['ansible_inventory']['all']['children']['worker']['hosts'].keys())

        row.append(control_hosts)
        row.append(worker_hosts)
        # row.append(value['experiment_metadata']['deployment_metadata']['job_id'])
        # row.append(value['experiment_metadata']['deployment_metadata']['job_site'])
        # row.append(value['experiment_metadata']['deployment_metadata']['job_started_ts'])
        # row.append(value['experiment_metadata']['deployment_metadata']['type'])
        # Extract experiment parameters
        factors = value['experiment_metadata']['factors']['exp_params']
        # row.append(factors['durationSeconds'])
        row.append(factors['instances'])
        try:
            row.append(factors['kafkaOnWorker'])
        except:
            row.append('')
        row.append(factors['load'])
        # row.append(factors['warmupSeconds'])
        # row.append(value['started_ts'])
        # row.append(value['stopped_ts'])

        csv_data.append(row)

    csv_data = [header] + sorted(csv_data[1:], key=lambda x: int(x[0]))
    # Convert csv_data to CSV format as a string using a StringIO buffer
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_data)

    # Copy to clipboard
    pyperclip.copy(output.getvalue())
    output.close()
