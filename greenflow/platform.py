import bpdb
from sh import kubectl, k3d
from shlex import split


class Platform:
    def pre_deploy(self):
        raise NotImplementedError()

    def post_deploy(self):
        raise NotImplementedError()

    def pre_destroy(self):
        raise NotImplementedError()

    def post_destroy(self):
        raise NotImplementedError()

    def get_platform_metadata(self) -> dict:
        raise NotImplementedError()


class MockPlatform:
    def pre_deploy(self):
        k3d(split("cluster delete"))
        pass

    def post_deploy(self):
        kubectl(split("config set-context k3d-k3s-default"))

    def pre_destroy(self):
        pass

    def post_destroy(self):
        pass

    def get_platform_metadata(self) -> dict:
        pass
