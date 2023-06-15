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
    generate_explore_url,
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
        self.db = TinyDB("storage/experiment-history.yaml", storage=serialization2)

    @property
    def current_exp(self):
        return Query().metadata.deployment_start_ts == g.deployment_start

    def _init_inputs(self):
        try:
            current_gin_config = self.current_exp_data["inputs"]["gin_config"]
        except KeyError:
            current_gin_config = {}
        result = always_merger.merge(
            current_gin_config, dict(get_readable_gin_config())
        )
        self.current_exp_data["inputs"]["gin_config"] = result

    def create_new_exp(self, platform):

        from .factors import factors

        _ = factors()

        self.db.get(Query().metadata.platform.job_id == platform.metadata["job_id"])

        self.current_exp_data = dict(
            inputs={},
            metadata={
                "deployment_start_ts": g.deployment_start,
            },
        )
        self._init_inputs()

        self.current_exp_id = self.db.insert(self.current_exp_data)
        print(f"Current exp id: {self.current_exp_id}")

    def _refresh_current_exp_data(self):
        try:
            doc_id = self.current_exp_id
            self.current_exp_id = doc_id
            self.current_exp_data = self.db.get(doc_id=doc_id)
        except AttributeError:
            print(
                "Missing current_exp_id ! Using last value of current_exp_data instead."
            )
            print("saving a backup just in case")
            self.current_exp_id = self.db.__len__()
            self.current_exp_data = self.db.get(doc_id=self.current_exp_id)
            self.current_exp_data["metadata"] = {
                "deployment_start_ts": self.current_exp_data["metadata"].get("deployment_start_ts",pendulum.now())
            }
            self.current_exp_data["inputs"] = {"gin_config": {}}
            self.db.insert(
                Document(self.current_exp_data, doc_id=self.current_exp_id + 1)
            )
            self.current_exp_id += 1

    def _commit(self):
        self.db.upsert(
            Document(
                self.current_exp_data,
                doc_id=self.current_exp_id,
            )
        )

    def _update_current_exp_data(self, new_data):
        self._refresh_current_exp_data()

        result = always_merger.merge(new_data, self.current_exp_data)

        self.current_exp_data = result
        self._commit()

    def wrap_up_exp(self):
        g.deployment_end = pendulum.now()
        self._refresh_current_exp_data()
        self._init_inputs()
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
        from .factors import factors

        current_gin_config = self.current_exp_data["inputs"]["gin_config"]
        result = always_merger.merge(
            current_gin_config, dict(get_readable_gin_config())
        )
        self.current_exp_data["inputs"]["gin_config"] = result

        self._commit()

    def write_grafana_dashboard_url(self) -> None:
        self._refresh_current_exp_data()
        self._update_current_exp_data(
            {
                "metadata": {
                    "explore_url": generate_explore_url(
                        start_ts=self.current_exp_data["metadata"][
                            "deployment_start_ts"
                        ],
                        end_ts=g.deployment_end,
                    ),
                    "dashboard_url": generate_grafana_dashboard_url(
                        start_ts=self.current_exp_data["metadata"][
                            "deployment_start_ts"
                        ],
                        end_ts=g.deployment_end,
                    ),
                }
            },
        )
