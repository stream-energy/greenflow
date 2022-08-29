import fire

from . import deploy, destroy


class Run(object):
    def deploy(self):
        return deploy.main()

    def destroy(self):
        return destroy.main()


if __name__ == "__main__":
    fire.Fire(Run)
