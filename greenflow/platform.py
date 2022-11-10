import bpdb
from sh import kubectl, k3d
from shlex import split

import gin


class Platform:
    def pre_setup(self):
        raise NotImplementedError()

    def post_setup(self):
        raise NotImplementedError()

    def pre_teardown(self):
        raise NotImplementedError()

    def post_teardown(self):
        raise NotImplementedError()

    def get_platform_metadata(self) -> dict:
        raise NotImplementedError()

    def setup(self) -> dict:
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
                "cluster create --registry-config ansible/project/registries.yaml --k3s-arg '--disable=traefik@server:0'"
            )
        )

    def teardown(self):
        self.pre_teardown()
        k3d(split("cluster delete"))
        self.post_teardown()
