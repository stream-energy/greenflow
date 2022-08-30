#!/usr/bin/env python3
import enoslib as en
from shlex import split
from sh import ansible_playbook, kubectl, helm, rsync, ssh
from time import sleep


def main():
    site = "lyon"
    # Enable rich logging
    _ = en.init_logging()
    network = en.G5kNetworkConf(type="prod", roles=["my_network"], site=site)

    conf = (
        en.G5kConf.from_settings(job_type="allow_classic_ssh", job_name="eesp-01")
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
    try:
        kubectl(
            split("delete -n monitoring statefulsets victoria-metrics-single-server")
        )
    except:
        pass
    sleep(5)
    provider.destroy()
    sleep(5)
    ssh(
        split(
            "h-0 rsync -rvPh --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 lyon.grid5000.fr:/home/***REMOVED***/k8s /home/g/"
        )
    )
    # import ansible_runner

    # ansible_runner.run()


if __name__ == "__main__":
    main()
