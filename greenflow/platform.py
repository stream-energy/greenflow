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
        from .g import g

        self.set_platform_metadata()
        with open(f"{g.gitroot}/ansible/inventory/hosts.yaml", "w") as f:
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
    def pre_provision(self):
        pass
        # k3d(split("cluster delete"))

    def provision(self):
        try:
            k3d(split("cluster create -c deploy/test-cluster.yaml"))
        except:
            pass

    def post_provision(self):
        # k3d kubeconfig get -a > ../kubeconfig
        with open("kubeconfig", "w") as f:
            k3d(split("kubeconfig get --all"), _out=f)
        kubectl(split("config set-context greenflow-test-cluster"))
        from .g import g

        print(g.deployment_type)

    def pre_teardown(self):
        pass

    def teardown(self):
        self.pre_teardown()
        k3d(split("cluster delete -c deploy/test-cluster.yaml"))
        self.post_teardown()

    def post_teardown(self):
        kubectl(split("config set-context exp"))

    def get_platform_metadata(self) -> dict:
        pass
