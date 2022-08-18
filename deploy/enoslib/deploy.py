#!/usr/bin/env python3
from shlex import split

import requests
from sh import ansible_playbook, helm, kubectl

import enoslib as en


def main():
    site = "lyon"
    # Enable rich logging
    _ = en.init_logging()
    network = en.G5kNetworkConf(type="prod", roles=["my_network"], site=site)

    conf = (
        en.G5kConf.from_settings(job_type="allow_classic_ssh", job_name="rsd-01")
        .add_network_conf(network)
        .add_machine(
            roles=["control"],
            cluster="taurus",
            nodes=1,
            primary_network=network,
        )
        .add_machine(
            roles=["worker"],
            cluster="taurus",
            nodes=1,
            primary_network=network,
        )
        .finalize()
    )
    provider = en.G5k(conf)
    roles, networks = provider.init()
    jobs = provider.driver.get_jobs()
    job_id = jobs[0].uid
    job_site = jobs[0].site

    uri = "https://api.grid5000.fr/3.0/sites/lyon/storage/home/***REMOVED***/access"

    requests.post(
        uri,
        json={"termination": {"job": job_id, "site": job_site}},
        auth=("***REMOVED***", "***REMOVED***"),
    )

    en.run_ansible(["gen-inventory.yaml"], roles=roles)
    # en.run_ansible(['k3s-setup.yaml'], roles=roles)

    ansible_playbook(split("k3s-setup.yaml -i inventory/g5k.ini"), _fg=True)
    ansible_playbook(
        split("helm-setup.yaml -i inventory/g5k.ini -t redeploy"), _fg=True
    )
    ansible_playbook(split("helm-setup.yaml -i inventory/g5k.ini"), _fg=True)
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
