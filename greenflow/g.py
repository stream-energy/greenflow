from functools import cached_property

import pendulum
import transaction
import ZODB

from .datatypes import DateTime, Deployment
from .platform import Platform


class _g:
    # __slots__ = ["deployment_end"]

    @cached_property
    def _platform(self) -> Platform:
        from .g5k import G5KPlatform

        return G5KPlatform()

    @cached_property
    def deployment_start(self) -> DateTime:
        return pendulum.now()

    @cached_property
    def deployment_end(self) -> DateTime:
        return pendulum.now()

    @cached_property
    def storage(self):
        from .tiny import ExpStorage

        return ExpStorage()

    @cached_property
    def root(self):
        connection = ZODB.connection("storage/current_deployment.fs")
        root = connection.root
        return root

    def reinit_deployment(self, platform):
        d = Deployment(platform.metadata)
        self.root.current_deployment = d
        self.root.current_deployment.last_updated = pendulum.now()
        transaction.commit()


g: _g = _g()
