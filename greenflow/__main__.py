import fire
import gin
from icecream import install

from . import deploy, destroy, run, platform

from sh import ssh
from shlex import split
from os import system


class RUN:
    def deploy(self):
        return deploy.deploy()

    def destroy(self):
        return destroy.destroy()

    def base(self):
        run.base()

    def mrun(self):
        run.mrun()

    def full(self, ginfile):
        gin.parse_config_file(ginfile)
        deploy.deploy()
        run.base()
        run.kafka()
        run.theo()
        run.exp()

    def e2e(self, ginfile):
        gin.parse_config_file(ginfile)
        deploy.deploy()
        run.base()
        run.kafka()
        run.theo()
        run.exp()
        destroy.destroy()

    def mock(self):
        gin.parse_config_file("params/mock.gin")
        deploy.deploy()
        destroy.destroy()

    def mdeploy(self):
        gin.parse_config_file("params/mock.gin")
        deploy.deploy()

    def sync(self):
        system(
            "ssh -t h-0 sudo rsync -aXxvPh --exclude '*cache*' --exclude '*tmp*' --exclude '*txn*' --exclude '*lock*' --info=progress2 /mnt/energystream1/ /root/energystream1-mirror"
        )
        ssh(split("h-0 docker restart greenflow-vm-1"))

    def exp(self):
        run.exp()

    def theo(self):
        run.theo()

    def kafka(self):
        run.kafka()


if __name__ == "__main__":
    install()
    gin.parse_config_file("params/default.gin")
    fire.Fire(RUN)
