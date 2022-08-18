#!/usr/bin/env python3
import enoslib as en
from shlex import split
from sh import ansible_playbook, kubectl, helm


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
    provider.destroy()


if __name__ == "__main__":
    main()
