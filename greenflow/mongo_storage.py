from box import Box
from persistent import Persistent
from typing_extensions import TypedDict, NotRequired, Dict, Any, Optional, List
from datetime import datetime
from copy import deepcopy
import pendulum
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId
from os import getenv


class ExperimentMetadata(TypedDict):
    factors: Dict[str, Any]
    results: Dict[str, Any]
    deployment_metadata: Dict[str, Any]
    dashboard_url: NotRequired[str]
    explore_url: NotRequired[str]


class ExperimentDoc(TypedDict):
    _id: NotRequired[ObjectId]
    exp_name: str
    experiment_description: str
    started_ts: str  # ISO8601 string
    stopped_ts: str  # ISO8601 string
    experiment_metadata: ExperimentMetadata


class Experiment(Persistent):
    def __init__(
        self,
        # exp_name: str,
        # experiment_description: str = "",
        # started_ts: Optional[str] = None,
        # stopped_ts: Optional[str] = None,
        # experiment_metadata: Optional[Dict[str, Any]] = None,
        # _id: Optional[ObjectId] = ObjectId(),
        **kwargs,
    ):
        from .deployment import Deployment
        from .factors import factors
        from .utils import generate_explore_url, generate_grafana_dashboard_url
        from entrypoint import load_gin

        # load_gin("ingest-kafka")
        kwargs = Box(kwargs, default_box=True, default_box_attr=None)
        experiment_metadata = kwargs.experiment_metadata
        exp_name = kwargs.exp_name
        experiment_description = kwargs.experiment_description

        # Handle experiment type which is a string within experiment_description "type=true"

        # import re
        # match = re.search(r'(\w+)=true', experiment_description)
        # if match:
        #     self.type = match.group(1)



        from .g import g

        self.exp_name = exp_name
        self.experiment_description = experiment_description
        now = pendulum.now()
        self.started_ts = kwargs.started_ts or now.to_iso8601_string()
        self.stopped_ts = kwargs.stopped_ts or now.to_iso8601_string()

        try:
            self.deployment_metadata = kwargs.experiment_metadata.deployment_metadata
        except AttributeError:
            self.deployment_metadata = deepcopy(g.root.current_deployment.metadata)
        # if not experiment_metadata:
        #     try:
        #         self.deployment_metadata = deepcopy(g.root.current_deployment.metadata)
        #     except AttributeError:
        #         g.root.current_deployment = Deployment(metadata={"type": "mock"})
        #         self.deployment_metadata = {}

        #     else:
        #         self.deployment_metadata = kwargs.experiment_metadata.deployment_metadata

        # Initialize experiment_metadata
        base_metadata = {
            "factors": factors(),
            "results": {},
            "deployment_metadata": self.deployment_metadata,
            "dashboard_url": "",
            "explore_url": "",
        }
        self.experiment_metadata = (
            deepcopy(experiment_metadata)
            if experiment_metadata
            else deepcopy(base_metadata)
        )

        self.factors = deepcopy(self.experiment_metadata.get("factors", factors()))
        started_ts = pendulum.parse(self.started_ts)
        stopped_ts = pendulum.parse(self.stopped_ts)

        self.results = deepcopy(self.experiment_metadata.get("results", {}))
        self._id = ObjectId() if not kwargs._id else kwargs._id

        # Add Prometheus metrics calculation here if needed
        # Similar to your original implementation

    def to_doc(self) -> ExperimentDoc:
        from .utils import generate_explore_url, generate_grafana_dashboard_url

        self.calculate_results()

        return ExperimentDoc(
            exp_name=self.exp_name,
            experiment_description=self.experiment_description,
            started_ts=self.started_ts,
            stopped_ts=self.stopped_ts,
            experiment_metadata=deepcopy(
                {
                    "factors": self.factors,
                    "results": self.results,
                    "deployment_metadata": self.deployment_metadata,
                    "dashboard_url": generate_grafana_dashboard_url(
                        started_ts=self.started_ts, stopped_ts=self.stopped_ts
                    ),
                    "explore_url": generate_explore_url(
                        started_ts=self.started_ts, stopped_ts=self.stopped_ts
                    ),
                }
            ),
        )

    @classmethod
    def from_doc(cls, doc: ExperimentDoc) -> "Experiment":
        return cls(**doc)

    # def to_dict(self) -> dict:
    #     """Convert experiment to dictionary format matching the document structure"""
    #     self.calculate_results()

    #     return deepcopy(
    #         {
    #             "exp_name": self.exp_name,
    #             "experiment_description": self.experiment_description,
    #             "started_ts": self.started_ts,
    #             "stopped_ts": self.stopped_ts,
    #             "experiment_metadata": self.experiment_metadata,
    #         }
    #     )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experiment":
        """Create an Experiment instance from a dictionary"""
        return cls(
            exp_name=data["exp_name"],
            experiment_description=data["experiment_description"],
            started_ts=data["started_ts"],
            stopped_ts=data["stopped_ts"],
            experiment_metadata=deepcopy(data["experiment_metadata"]),
        )

    def calculate_results(self):
        self.results = {}
        started_ts = pendulum.parse(self.started_ts)
        stopped_ts = pendulum.parse(self.stopped_ts)

        # url = getenv("PROMETHEUS_URL")

        # prom = PrometheusConnect(url=url)
        # data = MetricRangeDataFrame(
        #     prom.get_metric_range_data(
        #         f'scaph_host_energy_microjoules{{experiment_started_ts="{started_ts.to_iso8601_string()}"}}',
        #         start_time=started_ts.subtract(hours=96),
        #         end_time=started_ts.add(hours=96),
        #     )
        # )
        # grouped_max = data.groupby("instance")["value"].max()
        # grouped_min = data.groupby("instance")["value"].min()
        # joules = sum(grouped_max - grouped_min) / 10**6

        duration = (
            stopped_ts.diff(started_ts).seconds
            + stopped_ts.diff(started_ts).microseconds / 10**6
        )
        self.results["duration"] = duration
        # self.results["total_host_energy"] = joules
        # self.results["avg_host_power"] = joules / duration
        self.experiment_metadata["results"] = self.results

    def to_dict(self) -> dict:
        self.calculate_results()
        metadata = self.experiment_metadata
        params = metadata["factors"]["exp_params"]

        # Parse experiment description parameters first
        desc_params = {}

        desc_parts = self.experiment_description.split()
        for part in desc_parts:
            if "=" in part:
                key, value = part.split("=", 1)
                desc_params[key] = value  # Store without prefix initially

        # Define relevant parameters
        relevant_params = [
            "load",
            "durationSeconds",
            "messageSize",
            "broker_cpu",
            "broker_mem",
            "cluster",
            # "bw",
            "broker_replicas",
            "partitions",
            "replicationFactor",
            "producer_instances",
            "consumer_instances",
            "type",
        ]

        result = {
            "exp_id": str(self._id),
            "exp_name": self.exp_name,
            "started_ts": self.started_ts,
            "stopped_ts": self.stopped_ts,
            **metadata.get("results", {}),
        }

        # Filter and add parameters from both sources
        # Priority: metadata params first, then description params if not already present
        filtered_params = {}
        for param in relevant_params:
            if param in params:
                filtered_params[param] = params[param]
            elif param in desc_params:
                filtered_params[f"{param}"] = desc_params[param]

        # Ensure type is captured from description if present
        if "type" in desc_params and "type" not in filtered_params:
            filtered_params["type"] = desc_params["type"]

        if filtered_params["cluster"] == "ovhnvme":
            filtered_params["num_broker_nodes"] = 3
            filtered_params["num_worker_nodes"] = 1
        else:
            filtered_params["num_broker_nodes"] = len(
                self.experiment_metadata.deployment_metadata.ansible_inventory.all.children.broker.hosts
            )
            filtered_params["num_worker_nodes"] = len(
                self.experiment_metadata.deployment_metadata.ansible_inventory.all.children.worker.hosts
            )

        return {**result, **filtered_params}


class ExpStorage:
    def __init__(
        self,
        *,
        url: str = getenv("MONGO_URL", "mongodb://localhost:27017/"),
        db_name: str = "greenflow",
    ):
        self.client = MongoClient(url)
        self.db = self.client[db_name]
        self.collection: Collection[ExperimentDoc] = self.db.experiments
        self.results_collection: Collection[ExperimentDoc] = self.db.results

        # Update indexes for common queries
        self.collection.create_index("exp_name")
        self.collection.create_index("started_ts")
        self.collection.create_index("experiment_description")
        self.collection.create_index(
            "experiment_metadata.factors.exp_params"
        )  # Index for params

    def save_experiment(self, experiment: Experiment) -> ObjectId:
        doc = experiment.to_doc()
        result = self.collection.insert_one(doc)
        return result.inserted_id

    def commit_experiment(self) -> None:
        from .g import g

        g.root.current_experiment.calculate_results()
        doc = g.root.current_experiment.to_doc()
        result = self.collection.insert_one(doc)
        return result.inserted_id

    def find_experiments_by_name(self, name: str) -> List[Experiment]:
        docs = self.collection.find({"exp_name": name})
        return [Experiment.from_doc(doc) for doc in docs]

    def find_experiments_by_name(self, name: str) -> List[Experiment]:
        docs = self.collection.find({"exp_name": name})
        return [Experiment.from_doc(doc) for doc in docs]

    def find_experiments_by_params(self, params: Dict[str, Any]) -> List[Experiment]:
        """Find experiments matching specific experiment parameters"""
        query = {
            f"experiment_metadata.factors.exp_params.{k}": deepcopy(v)
            for k, v in params.items()
        }
        print(f"Query: {query}")
        docs = self.collection.find(query)
        # for doc in docs:
        #     print(f"Found document: {doc}")
        return [Experiment.from_doc(doc) for doc in docs]

    def find_experiments_by_deployment_ts(self, deployment_ts: str) -> List[Experiment]:
        docs = self.collection.find(
            {"experiment_metadata.deployment_metadata.job_started_ts": deployment_ts},
            sort=[("started_ts", -1)],  # 1 for ascending, -1 for descending
        )
        return [Experiment.from_doc(doc) for doc in docs]

    def find_experiments_by_timerange(self, start: str, end: str) -> List[Experiment]:
        docs = self.collection.find(
            {
                "started_ts": {
                    "$gte": start,
                    "$lte": end,
                }
            }
        )
        return [Experiment.from_doc(doc) for doc in docs]

    def get_all_experiments(self) -> List[Experiment]:
        docs = self.collection.find({})
        return [Experiment.from_doc(doc) for doc in docs]

    def update_experiment(self, experiment: Experiment) -> None:
        if not experiment._id:
            raise ValueError("Cannot update experiment without _id")
        self.collection.update_one(
            {"_id": experiment._id}, {"$set": experiment.to_doc()}
        )

    def delete_experiment(self, experiment_id: ObjectId) -> None:
        self.collection.delete_one({"_id": experiment_id})
