import pendulum
import persistent
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import pandas as pd
import pendulum
from os import getenv

from .deployment import Deployment


class Experiment(persistent.Persistent):
    def __init__(self, exp_name, experiment_description=""):
        from .factors import factors
        from .g import g

        self.factors = factors()
        self.results = {}
        try:
            self.deployment_metadata = g.root.current_deployment.metadata
        except AttributeError:
            g.root.current_deployment = Deployment(metadata={"type": "mock"})
            self.deployment_metadata = {}
        now = pendulum.now()
        self.started_ts = now.to_iso8601_string()
        self.stopped_ts = now.to_iso8601_string()
        self.exp_name = exp_name
        self.experiment_description = experiment_description

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

    def to_dict(self) -> dict:
        from .utils import generate_explore_url, generate_grafana_dashboard_url

        self.calculate_results()

        return dict(
            {
                "exp_name": self.exp_name,
                "experiment_description": self.experiment_description,
                "started_ts": self.started_ts.format("YYYY-MM-DDTHH:mm:ssZ"),
                "stopped_ts": self.stopped_ts.format("YYYY-MM-DDTHH:mm:ssZ"),
                "experiment_metadata": {
                    "factors": self.factors,
                    "results": self.results,
                    "deployment_metadata": self.deployment_metadata,
                    "dashboard_url": generate_grafana_dashboard_url(
                        started_ts=self.started_ts, stopped_ts=self.stopped_ts
                    ),
                    "explore_url": generate_explore_url(
                        started_ts=self.started_ts, stopped_ts=self.stopped_ts
                    ),
                },
            }
        )
