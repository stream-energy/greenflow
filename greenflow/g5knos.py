from functools import cached_property

import enoslib as en
import pendulum
import requests
import yaml

import gin

from .platform import Platform


@gin.register()
class G5KNixOSPlatform(Platform):
    @gin.register(denylist=["job_name"])
    def get_conf(
        self,
        *,
        job_name: str = "eesp",
        site: str = gin.REQUIRED,
        cluster: str = gin.REQUIRED,
        num_control: int = gin.REQUIRED,
        num_worker: int = gin.REQUIRED,
        num_broker: int = gin.REQUIRED,
        walltime: str = gin.REQUIRED,
        queue: str = gin.REQUIRED,
        project: str = gin.REQUIRED,
    ):
        network = en.G5kNetworkConf(type="prod", roles=["my_network"], site=site)
        import logging

        en.init_logging(level=logging.INFO)
        job_name = f"{job_name}-{cluster}"

        return (
            en.G5kConf.from_settings(
                job_type=["allow_classic_ssh", "exotic"],
                job_name=job_name,
                queue=queue,
                walltime=walltime,
                project=project,
                env_name="nixos-x86_64-linux",
                key="~/.ssh/id_g5k_rsa.pub",
            )
            .add_network_conf(network)
            .add_machine(
                roles=["control"],
                cluster=cluster,
                nodes=num_control,
                primary_network=network,
                reservable_disks=True,
            )
            .add_machine(
                roles=["worker"],
                cluster=cluster,
                nodes=num_worker,
                primary_network=network,
                reservable_disks=True,
            )
            .add_machine(
                roles=["broker"],
                cluster=cluster,
                nodes=num_broker,
                primary_network=network,
                reservable_disks=True,
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
        from .g import g

        self.metadata["type"] = "g5k"
        self.metadata["job_id"] = self.jobs[0].uid
        self.metadata["job_site"] = self.jobs[0].site
        self.metadata["job_started_ts"] = (
            pendulum.from_format(
                str(self.jobs[0].attributes["started_at"]),
                "X",
                tz="UTC",
            )
            .in_timezone("Europe/Paris")
            .format("YYYY-MM-DDTHH:mm:ssZ")
        )
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
                elif grp == "broker":
                    self.metadata["ansible_inventory"]["all"]["children"][grp]["hosts"][
                        host.alias
                    ] = {"kubernetes_role": "broker"}
        g.reinit_deployment(self)

    def handle_hardware_quirks(self):
        # if self.get_conf().cluster == "paravance":
        from .playbook import quirks

        quirks("paravance")
        # Run the parasilo playbook

    def post_provision(self):
        from .g import g
        from .playbook import deploy_nos_k3s

        self.set_platform_metadata()

        with open(f"{g.gitroot}/ansible/inventory/hosts.yaml", "w") as f:
            yaml.dump(self.get_ansible_inventory(), f)

        # self.handle_hardware_quirks()
        deploy_nos_k3s()

        # Handle k3s config
        # Create /etc/lollypops
        # Deploy all of the templates
        # Call nix run


    def pre_teardown(self):
        pass

    def teardown(self):
        self.pre_teardown()
        self.provider = en.G5k(self.get_conf())
        self.provider.destroy()
        self.post_teardown()

    def get_ansible_inventory(self) -> dict:
        return self.metadata["ansible_inventory"]

    def post_teardown(self):
        pass
