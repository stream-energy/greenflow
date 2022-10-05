import enoslib as en
import fire
import gin
from icecream import install

from . import deploy, destroy


class RUN:
    def deploy(self):
        return deploy.deploy()

    def destroy(self):
        return destroy.destroy()


if __name__ == "__main__":
    _ = en.init_logging()
    install()
    gin.parse_config_file("params/default.gin")
    # TODO: Add support for MockProvider
    fire.Fire(RUN)
