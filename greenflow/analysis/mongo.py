from os import getenv
from box import Box
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
import logging
from typing import Any, Callable
import pandas as pd
import pendulum
from tinydb.table import Document

import time
import requests
from prometheus_api_client import MetricRangeDataFrame


# def get_experiments():
#     from ..g import g

#     experiments = {exp.doc_id: exp for exp in g.storage.experiments.all()}
#     return experiments


def sort_by_time(exp_id, experiments):
    date_time_str = experiments[exp_id]["started_ts"]
    return pendulum.parse(date_time_str)


def get_observed_throughput_of_last_experiment(
    minimum_current_ts: pendulum.DateTime,
) -> float:
    from ..g import g
    from ..mongo_storage import ExpStorage, Experiment
    import logging

    url = getenv("PROMETHEUS_URL")
    prom = PrometheusConnect(url=url)
    storage: ExpStorage = g.storage

    matching_experiment = storage.collection.find(
        {
            "experiment_metadata.deployment_metadata.job_started_ts": g.root.current_deployment.started_ts,
            "started_ts": {"$gte": minimum_current_ts.to_iso8601_string()},
        },
        sort=[("started_ts", -1)],
        limit=1,
    ).to_list()
    if not matching_experiment:
        print(f"No experiments found after {minimum_current_ts}")
        return float("NaN")

    # Since we are using VictoriaMetrics, there's an additional flush required
    requests.get(f"{url}/internal/force_flush")
    time.sleep(5)

    latest_exp = Experiment.from_doc(matching_experiment[0])
    latest_exp = Box(latest_exp.to_dict())

    # Extract timestamps
    started_ts = pendulum.parse(latest_exp.started_ts)
    stopped_ts = pendulum.parse(latest_exp.stopped_ts)

    # Sanity check
    if started_ts < minimum_current_ts:
        print(
            f"Warning: Latest experiment started at {started_ts}, which is before the minimum timestamp {minimum_current_ts}"
        )
        return float("NaN")

    # Determine the namespace
    namespace = "redpanda" if "redpanda" in latest_exp.exp_name else "default"

    # Construct the query
    query = f'kminion_kafka_topic_high_water_mark_sum{{namespace="{namespace}", topic_name="input", experiment_started_ts="{latest_exp.started_ts}"}}'

    try:
        # Get the data from Prometheus
        data = MetricRangeDataFrame(
            prom.get_metric_range_data(
                query,
                start_time=started_ts,
                end_time=stopped_ts,
            )
        )

        # Calculate the observed throughput
        max_watermark = data["value"].max()
        duration = (stopped_ts - started_ts).total_seconds()
        try:
            duration = latest_exp.durationSeconds
        except KeyError:
            pass

        observed_throughput = max_watermark / duration

        logging.warning({"observed_throughput": observed_throughput})
        return observed_throughput

    except KeyError:
        logging.error("No data found for the latest experiment")
        logging.error("Query used was %s", query)
        raise
