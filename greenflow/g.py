from functools import cached_property

import pendulum
import transaction
import ZODB

class _g:
    @cached_property
    def storage(self):
        from .storage import ExpStorage

        return ExpStorage()

    @cached_property
    def gitroot(self):
        from os import environ

        return environ["GITROOT"]

    @cached_property
    def root(self):
        connection = ZODB.connection(f"{self.gitroot}/storage/current_deployment.fs")
        root = connection.root
        return root

    def reinit_deployment(self, platform):
        from .deployment import Deployment

        d = Deployment(platform.metadata)
        self.root.current_deployment = d
        self.root.current_deployment.last_updated = pendulum.now()
        transaction.commit()

    def init_exp(self):
        from .experiment import Experiment

        e = Experiment()
        self.root.current_experiment = e
        transaction.commit()

    def end_exp(self):
        exp = self.root.current_experiment
        exp.stopped_ts = pendulum.now()

        # To avoid polluting, do not write to disk if shorter than 2 minutes
        if exp.stopped_ts.diff(exp.started_ts).minutes < 2:
            self.root.current_experiment = None
            transaction.commit()
            return
        g.storage.commit_experiment()


g: _g = _g()
