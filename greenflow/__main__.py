import fire
import gin
from icecream import install

from . import deploy, destroy, run, platform


class RUN:
    def deploy(self):
        return deploy.deploy()

    def destroy(self):
        return destroy.destroy()

    def run(self):
        run.run()
        # destroy.destroy()

    def mrun(self):
        run.mrun()

    def full(self):
        deploy.deploy()
        run.run()
        destroy.destroy()

    def mock(self):
        gin.parse_config_file("params/mock.gin")
        deploy.deploy()
        destroy.destroy()

    def mdeploy(self):
        gin.parse_config_file("params/mock.gin")
        deploy.deploy()


if __name__ == "__main__":
    install()
    gin.parse_config_file("params/default.gin")
    fire.Fire(RUN)
