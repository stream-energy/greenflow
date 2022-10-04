import gin

import bpdb


class Platform:
    def __init__(self, *, ansible_inventory_file_path="/tmp/inventory.ini"):
        self.ansible_inventory_file_path = ansible_inventory_file_path

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
