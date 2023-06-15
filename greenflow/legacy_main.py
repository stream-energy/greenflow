import sys
from os import system
from shlex import split

import fire
import gin
from icecream import install
from sh import helm, ssh

from . import base, destroy, provision

print(sys.argv)


class RUN:
    def upto(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        provision.provision()
        base.base()
        base.kafka()
        base.theo()

    def exp(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        base.exp()

    def theo(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        base.theo()

    def kafka(self):
        base.kafka()

    def deploy(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        return provision.provision()

    def destroy(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        return destroy.destroy()

    def mock_destroy(self):
        return destroy.mock_destroy()

    def blowaway(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        return destroy.blowaway()

    def killjob(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        destroy.mock_destroy()
        destroy.killjob()

    def base(self):
        base.base()

    def mrun(self):
        base.mrun()

    def full(self, ginfile):
        gin.parse_config_file(ginfile)
        provision.provision()
        base.base()
        base.kafka()
        base.theo()
        base.exp()

    def tight(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        # deploy.deploy()
        # run.base()
        # run.vm()
        # run.vm()
        # run.kafka()
        # run.theo()
        base.exp()
        c = input("Press any key to mock_destroy or q to exit")
        if c == "q":
            return
        destroy.mock_destroy()
        helm(split("uninstall theodolite"))
        # helm(split("uninstall strimzi"))

    def e2e(self):
        gin.parse_config_file("params/1worker-1resources-kafka.gin")
        # gin.parse_config_file(ginfile)
        provision.provision()
        base.base()
        base.vm()
        base.kafka()
        base.theo()
        base.exp()
        # c = input("Press any key to mock_destroy or q to exit")
        # if c == "q":
        #     return
        # destroy.mock_destroy()
        # c = input("Press any key to vm or q to exit")
        # if c == "q":
        #     return
        destroy.destroy()
        # run.vm()
        # destroy.blowaway()

    def vm(self):
        ginfile = "params/1worker-1resources-kafka.gin"
        gin.parse_config_file(ginfile)
        # deploy.deploy()
        # run.base()
        base.vm()

    def redpanda(self):
        ginfile = "params/1worker-3resources-redpanda.gin"
        gin.parse_config_file(ginfile)
        # deploy.deploy()
        # run.base()
        base.redpanda()
        # run.theo()
        # run.exp()
        # destroy.destroy()

    def mock(self):
        gin.parse_config_file("params/mock.gin")
        provision.provision()
        destroy.destroy()

    def mdeploy(self):
        gin.parse_config_file("params/mock.gin")
        provision.provision()

    def sync(self):
        system(
            "ssh -t h-0 sudo rsync -aXxvPh --exclude '*cache*' --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 /mnt/energystream1/ /root/energystream1-mirror"
        )
        ssh(split("h-0 docker restart greenflow-vm-1"))


if __name__ == "__main__":
    install()
    gin.parse_config_file("params/1worker-1resources-kafka.gin")
    fire.Fire(RUN)
