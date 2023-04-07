from multiprocessing import Process

import ansible_runner
import gin
import requests
import yaml
from icecream import ic
import pendulum

from .platform import Platform

from .g import g
from shlex import split
from time import sleep

import gin
from sh import kubectl, ssh


@gin.register(denylist=["job_name"])
class G5KPlatform(Platform):
    @staticmethod
    def __get_conf(**kwargs):
        import enoslib as en

        network = en.G5kNetworkConf(
            type="prod", roles=["my_network"], site=kwargs["site"]
        )

        conf = (
            en.G5kConf.from_settings(
                job_type="allow_classic_ssh",
                job_name=kwargs["job_name"],
                queue=kwargs["queue"],
                walltime=kwargs["walltime"],
            )
            .add_network_conf(network)
            .add_machine(
                roles=["control"],
                cluster=kwargs["cluster"],
                nodes=kwargs["num_control"],
                primary_network=network,
            )
            .add_machine(
                roles=["worker"],
                cluster=kwargs["cluster"],
                nodes=kwargs["num_worker"],
                primary_network=network,
            )
            .finalize()
        )
        return conf

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
        import enoslib as en

        super().__init__()
        self.metadata = {}
        _ = en.init_logging()
        conf = G5KPlatform.__get_conf(
            job_name=job_name,
            site=site,
            cluster=cluster,
            num_control=num_control,
            num_worker=num_worker,
            walltime=walltime,
            queue=queue,
        )
        self.conf = conf
        self.provider = en.G5k(self.conf)
        jobs = self.provider.driver.get_jobs()

        try:
            self.metadata["job_id"] = jobs[0].uid
            self.metadata["job_site"] = jobs[0].site
            self.metadata["job_started_ts"] = pendulum.from_format(
                str(jobs[0].attributes["started_at"]),
                "X",
                tz="UTC",
            ).in_timezone("Europe/Paris")

            self.roles, self.networks = self.provider.init()
        except IndexError:
            print("Job not already running. Will start new job")
            self.roles, self.networks = self.provider.init()
            jobs = self.provider.driver.get_jobs()
            self.metadata["job_id"] = jobs[0].uid
            self.metadata["job_site"] = jobs[0].site
            self.metadata["job_started_ts"] = pendulum.from_format(
                str(jobs[0].attributes["started_at"]),
                "X",
                tz="UTC",
            )

    @gin.register
    def setup(self):
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
        for grp, hostset in self.roles.items():
            inv["all"]["children"][grp] = {}
            inv["all"]["children"][grp]["hosts"] = {}
            for host in hostset:
                if grp == "control":
                    inv["all"]["children"][grp]["hosts"][host.alias] = {
                        "kubernetes_role": "control_plane"
                    }
                elif grp == "worker":
                    inv["all"]["children"][grp]["hosts"][host.alias] = {
                        "kubernetes_role": "node"
                    }

        self.metadata["nodes"] = inv
        self.post_setup()
        return inv

    def pre_setup(self):
        pass

    def post_setup(self):
        g.storage._update_current_exp_data({"metadata": {"platform": self.metadata}})

        self.enable_g5k_nfs_access()

    def enable_g5k_nfs_access(self):
        from os.path import expanduser

        with open(expanduser("~") + "/.python-grid5000.yaml") as f:
            g5kcreds = yaml.safe_load(f)

        # home_uri = f"https://api.grid5000.fr/3.0/sites/{self.job_site}/storage/home/{g5kcreds['username']}/access"
        uri = f"https://api.grid5000.fr/stable/sites/lyon/storage/storage1/energystream1/access"

        requests.post(
            uri,
            json={
                "termination": {
                    "job": self.metadata["job_id"],
                    "site": self.metadata["job_site"],
                }
            },
            auth=(g5kcreds["username"], g5kcreds["password"]),
        )

    # def get_platform_metadata(self) -> dict[str, str]:
    #     jobs = self.provider.driver.get_jobs()
    #     return dict(job_id=jobs[0].uid)

    def pre_teardown(self):
        pass
        # ssh(
        #     split(
        #         "h-0 sudo rsync -aXxvPh --exclude '*cache*' --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 /mnt/energystream1 /root/k8s-pvs"
        #     )
        # )
        # ssh(split("h-0 docker restart vm"))

    def teardown(self):
        self.pre_teardown()
        self.provider.destroy()
        self.post_teardown()

    def post_teardown(self):
        pass
