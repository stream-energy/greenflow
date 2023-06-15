import sys
from os import system
from shlex import split

import fire
import gin
from icecream import install
from sh import helm, ssh

from . import base, destroy, provision


class RUN:
    def provision(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        provision.provision()

    def base(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        base.base()

    def deploy(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        base.deploy_k3s()

    def strimzi(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        base.strimzi()

    def theodolite(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        base.theodolite()


if __name__ == "__main__":
    install()
    gin.parse_config_file("params/1worker-1resources-kafka.gin")
    fire.Fire(RUN)
