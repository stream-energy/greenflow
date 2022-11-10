from functools import cached_property

import pendulum
from tinydb import Query, TinyDB
from tinydb.queries import QueryInstance
from tinydb.storages import JSONStorage
from tinydb.table import Document
from tinydb_serialization import SerializationMiddleware, Serializer

from deepmerge import always_merger

from .g import g
from .utils import (
    DateTimeSerializer,
    YAMLStorage,
    generate_grafana_dashboard_url,
    get_readable_gin_config,
)


class ExpStorage:
    def __init__(self) -> None:
        # serialization1 = SerializationMiddleware(JSONStorage)
        serialization2 = SerializationMiddleware(YAMLStorage)
        # serialization1.register_serializer(DateTimeSerializer(), "Pendulum")
        serialization2.register_serializer(DateTimeSerializer(), "Pendulum")
        # self.db1 = TinyDB(
        #     "storage/experiment-history.json",
        #     sort_keys=True,
        #     indent=4,
        #     separators=(",", ": "),
        #     storage=serialization1,
        # )
        self.db2 = TinyDB("storage/experiment-history.yaml", storage=serialization2)

    @property
    def current_exp(self):
        return Query().metadata.deployment_start_ts == g.deployment_start

    def create_new_exp(self):
        self.current_exp_data = dict(
            metadata={"deployment_start_ts": g.deployment_start},
        )
        self.current_exp_id = self.db2.insert(self.current_exp_data)
        self.write_gin_config()

    def _update_current_exp_data(self, new_data):
        result = always_merger.merge(self.current_exp_data, new_data)
        self.current_exp_data = result
        self.db2.upsert(
            Document(
                self.current_exp_data,
                doc_id=self.current_exp_id,
            )
        )

    def wrap_up_exp(self):
        # g.deployment_end = pendulum.now()
        self._update_current_exp_data(
            {
                "metadata": {
                    "deployment_end_ts": g.deployment_end,
                }
            }
        )
        self.write_grafana_dashboard_url()
        self.write_gin_config()

    def write_gin_config(self) -> None:
        self._update_current_exp_data(
            {"inputs": {"gin_config": dict(get_readable_gin_config())}},
        )

    def write_grafana_dashboard_url(self) -> None:
        self._update_current_exp_data(
            {"metadata": {"dashboard_url": generate_grafana_dashboard_url()}},
        )
