#!/usr/bin/env python3
from shlex import split
from multiprocessing import Process

import enoslib as en
import gin
import pendulum
import requests
import yaml
from bpdb import set_trace
from sh import ansible_playbook, helm, kubectl


@gin.configurable
def gen_g5k_config(
    *,
    job_name: str = "eesp-01",
    site: str = gin.REQUIRED,
    cluster: str = gin.REQUIRED,
    num_control: int = gin.REQUIRED,
    num_worker: int = gin.REQUIRED,
    job_id: int = None,
) -> en.infra.enos_g5k.configuration.Configuration:

    network = en.G5kNetworkConf(type="prod", roles=["my_network"], site=site)
    conf = (
        en.G5kConf.from_settings(job_type="allow_classic_ssh", job_name=job_name)
        .add_network_conf(network)
        .add_machine(
            roles=["control"],
            cluster=cluster,
            nodes=num_control,
            primary_network=network,
        )
        .add_machine(
            roles=["worker"],
            cluster=cluster,
            nodes=num_worker,
            primary_network=network,
        )
        .finalize()
    )
    return conf


def enable_g5k_nfs_access(*, provider):
    g5kcreds = {}
    with open(".python-grid5000.yaml") as f:
        g5kcreds = yaml.safe_load(f)

    jobs = provider.driver.get_jobs()

    job_id = jobs[0].uid
    job_site = jobs[0].site
    uri = f"https://api.grid5000.fr/3.0/sites/{job_site}/storage/home/{g5kcreds['username']}/access"

    requests.post(
        uri,
        json={"termination": {"job": job_id, "site": job_site}},
        auth=(g5kcreds["username"], g5kcreds["password"]),
    )


@gin.configurable
def deploy_exp_on_g5k(
    *,
    g5k_config: en.infra.enos_g5k.configuration.Configuration,
):
    provider = en.G5k(g5k_config)
    roles, networks = provider.init()
    p = Process(target=enable_g5k_nfs_access, kwargs={"provider": provider})
    p.start()
    en.run_ansible(["gen-inventory.yaml"], roles=roles)
    ansible_playbook(split("k3s-setup.yaml -i inventory/g5k.ini"), _fg=True)
    p.join()
    ansible_playbook(
        split("helm-setup.yaml -i inventory/g5k.ini -t redeploy"), _fg=True
    )
    ansible_playbook(split("helm-setup.yaml -i inventory/g5k.ini"), _fg=True)


def main():
    _ = en.init_logging()

    gin.parse_config_file("params/default.gin")
    deploy_exp_on_g5k()

    try:
        port_forward_process = kubectl(
            split(
                "port-forward -n monitoring svc/victoria-metrics-single-server 8428:8428"
            ),
            _bg=True,
        )
    except:
        pass


if __name__ == "__main__":
    main()
