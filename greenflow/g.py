import pendulum
from .storage import ExpStorage

from .datatypes import DateTime

deployment_start: DateTime = pendulum.now()
storage: ExpStorage = ExpStorage()
