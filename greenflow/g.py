from functools import cached_property

import pendulum
import transaction
import ZODB
import gin

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
        self.root.current_deployment.last_updated = pendulum.now().to_iso8601_string()
        transaction.commit()

    def init_exp(self, exp_name, experiment_description=''):
        from .experiment import Experiment

        e = Experiment(exp_name, experiment_description)
        self.root.current_experiment = e
        transaction.commit()

    def end_exp(self):
        exp = self.root.current_experiment
        stopped_ts = pendulum.now()
        exp.stopped_ts = stopped_ts.to_iso8601_string()


        # # To avoid polluting, do not write to disk if shorter than 2 minutes
        # if stopped_ts.diff(pendulum.parse(exp.started_ts)).minutes < 2:
        #     self.root.current_experiment = None
        #     transaction.commit()
        #     return
        g.storage.commit_experiment()


g: _g = _g()

# if __name__ == "__main__":
#     import greenflow.platform
#     def load_gin(exp_name):
#         gin.parse_config_files_and_bindings(
#             [
#                 f"{g.gitroot}/gin/g5k-defaults.gin",
#                 f"{g.gitroot}/gin/{exp_name}.gin",
#             ],
#             []
#         )

#     load_gin("uc3-flink")
#     # You can call the various class methods here. Examples:
#     # g.reinit_deployment(platform)
#     g.init_exp("uc3-flink")
#     g.end_exp()

#     # Note: The necessary arguments must be provided to the methods.
#     pass
