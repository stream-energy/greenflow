from shlex import split

import bpdb
import gin
import persistent
import transaction
import yaml
from sh import k3d, kubectl


class Platform(persistent.Persistent):
    def set_platform_metadata(self):
        raise NotImplementedError()

    def pre_provision(self):
        raise NotImplementedError()

    def post_provision(self):
        self.set_platform_metadata()
        with open("./ansible/inventory/hosts.yaml", "w") as f:
            yaml.dump(self.get_ansible_inventory(), f)
        transaction.commit()

    def pre_teardown(self):
        raise NotImplementedError()

    def post_teardown(self):
        raise NotImplementedError()

    def get_platform_metadata(self) -> dict:
        raise NotImplementedError()

    def provision(self) -> dict:
        """Deploys Resources.
        Produces a dict that can be written into an ansible hosts.yaml file"""
        raise NotImplementedError()

    def get_ansible_inventory(self) -> dict:
        "Produces a dict that can be written into an ansible hosts.yaml file"
        raise NotImplementedError()


@gin.register()
class MockPlatform:
    def pre_setup(self):
        pass
        # k3d(split("cluster delete"))

    def post_setup(self):
        kubectl(split("config set-context k3d-k3s-default"))

    def pre_teardown(self):
        pass

    def post_teardown(self):
        kubectl(split("config set-context exp"))

    def get_platform_metadata(self) -> dict:
        pass

    def setup(self):
        k3d(
            split(
                "cluster create -i 'docker.io/rancher/k3s:v1.24.7-k3s1' --k3s-arg '--disable=traefik@server:0'"
            )
        )

    def teardown(self):
        self.pre_teardown()
        k3d(split("cluster delete"))
        self.post_teardown()
