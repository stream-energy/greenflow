from tinydb import Query, TinyDB
from tinydb.queries import QueryInstance
from tinydb.storages import JSONStorage
from tinydb_serialization import Serializer, SerializationMiddleware

from . import g
from .utils import get_readable_gin_config, YAMLStorage, DateTimeSerializer


class ExpStorage:
    def __init__(self) -> None:
        serialization1 = SerializationMiddleware(JSONStorage)
        serialization2 = SerializationMiddleware(YAMLStorage)
        serialization1.register_serializer(DateTimeSerializer(), "Pendulum")
        serialization2.register_serializer(DateTimeSerializer(), "Pendulum")
        self.db1 = TinyDB(
            "storage/experiment-history.json",
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
            storage=serialization1,
        )
        self.db2 = TinyDB("storage/experiment-history.yaml", storage=serialization2)
        self.current_exp: QueryInstance

    def create_new_exp(self):
        # TODO: Input deployment timestamp and do an insert
        self.db1.insert({"metadata": {"deployment_ts": g.deployment_start}})
        self.db2.insert({"metadata": {"deployment_ts": g.deployment_start}})
        self.current_exp = Query().metadata.deployment_ts == g.deployment_start

    def write_gin_config(self) -> None:
        self.db1.upsert(
            {"inputs": {"gin_config": dict(get_readable_gin_config())}},
            self.current_exp,
        )
        self.db2.upsert(
            {"inputs": {"gin_config": dict(get_readable_gin_config())}},
            self.current_exp,
        )
