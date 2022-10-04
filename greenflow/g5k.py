from multiprocessing import Process

import ansible_runner
import enoslib as en
import gin
import requests
import yaml
from icecream import ic

from .platform import Platform

from . import g


@gin.register(denylist=["job_name"])
class G5KPlatform(Platform):
    @gin.register(denylist=["job_name"])
    def __init__(
        self,
        *,
        job_name: str = "eesp-01",
        site: str = gin.REQUIRED,
        cluster: str = gin.REQUIRED,
        num_control: int = gin.REQUIRED,
        num_worker: int = gin.REQUIRED,
        walltime: str = gin.REQUIRED,
        queue: str = gin.REQUIRED,
    ):

        super().__init__()
        network = en.G5kNetworkConf(type="prod", roles=["my_network"], site=site)
        conf = (
            en.G5kConf.from_settings(
                job_type="allow_classic_ssh",
                job_name=job_name,
                queue=queue,
                walltime=walltime,
            )
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
        self.conf = conf
        self.provider = en.G5k(self.conf)

    @gin.register
    def deploy(self):
        roles, networks = self.provider.init()
        # en.run_ansible(
        #     ["gen-inventory.yaml"],
        #     roles=roles,
        #     extra_vars={
        #         "ansible_inventory_file_path": self.ansible_inventory_file_path
        #     },
        # )
        inv = {"all": {"children": {}}}
        #     { "all": { "hosts": { "vm1.nodekite.com": null, "vm2.nodekite.com": null }, "children": { "web": { "hosts": {
        #     "vm3.nodekite.com": null, "vm4.nodekite.com": null } }, "db": { "hosts": { "vm5.nodekite.com": null, "vm6.nodekite.com": null }
        # } } } }
        for grp, hostset in roles.items():
            inv["all"]["children"][grp] = {}
            inv["all"]["children"][grp]["hosts"] = {}
            for host in hostset:
                inv["all"]["children"][grp]["hosts"][host.alias] = None

        return inv

    def pre_deploy(self):
        pass

    def post_deploy(self):
        jobs = self.provider.driver.get_jobs()

        self.job_id = jobs[0].uid
        self.job_site = jobs[0].site

        self.enable_g5k_nfs_access()

    def enable_g5k_nfs_access(self):
        from os.path import expanduser

        with open(expanduser("~") + "/.python-grid5000.yaml") as f:
            g5kcreds = yaml.safe_load(f)

        uri = f"https://api.grid5000.fr/3.0/sites/{self.job_site}/storage/home/{g5kcreds['username']}/access"

        requests.post(
            uri,
            json={"termination": {"job": self.job_id, "site": self.job_site}},
            auth=(g5kcreds["username"], g5kcreds["password"]),
        )

    def get_platform_metadata(self) -> dict[str, str]:
        return dict(job_id=self.job_id)

    def pre_destroy(self):
        pass

    def destroy(self):
        self.pre_destroy()
        self.provider.destroy()
        self.post_destroy()

    def post_destroy(self):
        pass
