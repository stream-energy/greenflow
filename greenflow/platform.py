import gin

import bpdb


@gin.configurable
class Platform:
    @gin.configurable
    def __init__(self, *, ansible_inventory_file_path=gin.REQUIRED):
        self.ansible_inventory_file_path = ansible_inventory_file_path

    def pre_deploy(self):
        pass

    def post_deploy(self):
        pass

    def pre_destroy(self):
        pass

    def post_destroy(self):
        pass
