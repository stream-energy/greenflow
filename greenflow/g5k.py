from functools import cached_property

import enoslib as en
import gin
import pendulum
import requests
import yaml

from .g import g
from .platform import Platform


@gin.register()
class G5KPlatform(Platform):
    @gin.register(denylist=["job_name"])
    def get_conf(
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
        network = en.G5kNetworkConf(type="prod", roles=["my_network"], site=site)

        return (
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

    def __init__(self):
        super().__init__()
        self.metadata = {}
        _ = en.init_logging()

    def pre_provision(self):
        pass

    @gin.register
    def provision(self):
        self.provider = en.G5k(self.get_conf())

        self.roles, self.networks = self.provider.init()
        self.jobs = self.provider.driver.get_jobs()

    def set_platform_metadata(self):
        self.metadata["type"] = "g5k"
        self.metadata["job_id"] = self.jobs[0].uid
        self.metadata["job_site"] = self.jobs[0].site
        self.metadata["job_started_ts"] = pendulum.from_format(
            str(self.jobs[0].attributes["started_at"]),
            "X",
            tz="UTC",
        ).in_timezone("Europe/Paris")
        self.metadata["ansible_inventory"] = {"all": {"children": {}}}
        for grp, hostset in self.roles.items():
            self.metadata["ansible_inventory"]["all"]["children"][grp] = {}
            self.metadata["ansible_inventory"]["all"]["children"][grp]["hosts"] = {}
            for host in hostset:
                if grp == "control":
                    self.metadata["ansible_inventory"]["all"]["children"][grp]["hosts"][
                        host.alias
                    ] = {"kubernetes_role": "control_plane"}
                elif grp == "worker":
                    self.metadata["ansible_inventory"]["all"]["children"][grp]["hosts"][
                        host.alias
                    ] = {"kubernetes_role": "node"}
        g.reinit_deployment(self)

    def post_provision(self):
        self.set_platform_metadata()
        self.enable_g5k_nfs_access()

    def enable_g5k_nfs_access(self):
        from os.path import expanduser

        with open(expanduser("~") + "/.python-grid5000.yaml") as f:
            g5kcreds = yaml.safe_load(f)

        uri = "https://api.grid5000.fr/stable/sites/lyon/storage/storage1/energystream1/access"

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

    def get_ansible_inventory(self) -> dict:
        return self.metadata["ansible_inventory"]

    def post_teardown(self):
        pass
