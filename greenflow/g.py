from functools import cached_property

import pendulum
import transaction
import ZODB
import gin

from .factors import factors


@gin.configurable()
class _g:
    def __init__(
        self,
        deployment_type: str = gin.REQUIRED,
    ):
        self.deployment_type = deployment_type
        if deployment_type == "test":
            import os
            os.environ["EXPERIMENT_STORAGE_URL"] = os.environ["TEST_EXPERIMENT_STORAGE_URL"]
            os.environ["PROMETHEUS_URL"] = os.environ["TEST_PROMETHEUS_URL"]
            os.environ["EXPERIMENT_PUSHGATEWAY_URL"] = os.environ[
                "TEST_EXPERIMENT_PUSHGATEWAY_URL"
            ]
            os.environ["DASHBOARD_BASE_URL"] = os.environ["TEST_DASHBOARD_BASE_URL"]

    @cached_property
    def storage(self):
        from .storage import ExpStorage
        from unittest.mock import Mock

        if self.deployment_type == "production":
            return ExpStorage()
        elif self.deployment_type == "test":
            return ExpStorage(
                path=f"{self.gitroot}/storage/test_experiment-history.yaml"
            )

    @cached_property
    def gitroot(self):
        from os import environ

        return environ["GITROOT"]

    @cached_property
    def root(self):
        if self.deployment_type == "production":
            storage_path = f"{self.gitroot}/storage/current_deployment.fs"
        elif self.deployment_type == "test":
            storage_path = f"{self.gitroot}/storage/test_deployment.fs"
        connection = ZODB.connection(storage_path)
        root = connection.root
        return root

    def reinit_deployment(self, platform):
        from .deployment import Deployment

        d = Deployment(platform.metadata)
        self.root.current_deployment = d
        self.root.current_deployment.last_updated = pendulum.now().to_iso8601_string()
        transaction.commit()

    def init_exp(self, experiment_description):
        from .experiment import Experiment

        exp_name = factors()["exp_name"]

        e = Experiment(exp_name, experiment_description)
        self.root.current_experiment = e
        transaction.commit()

    def end_exp(self):
        from .g import g
        stopped_ts = pendulum.now()
        self.root.current_experiment.stopped_ts = stopped_ts.to_iso8601_string()
        transaction.commit()

        # # To avoid polluting, do not write to disk if shorter than 2 minutes
        # if stopped_ts.diff(pendulum.parse(exp.started_ts)).minutes < 2:
        #     self.root.current_experiment = None
        #     transaction.commit()
        #     return
        # #TODO: A bit sus
        g.storage.commit_experiment()

    @staticmethod
    def get_g() -> "_g":
        return _g()
