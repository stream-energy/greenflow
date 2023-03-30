import pendulum

from functools import cached_property

from .datatypes import DateTime

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
        from .storage import ExpStorage

        return ExpStorage()


g: _g = _g()
