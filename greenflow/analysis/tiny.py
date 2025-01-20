from os import getenv
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
import logging
from typing import Any, Callable
import pandas as pd
import pendulum
from tinydb.table import Document

import requests
from prometheus_api_client import MetricRangeDataFrame


def get_experiments():
    from ..g import g

    experiments = {exp.doc_id: exp for exp in g.storage.experiments.all()}
    return experiments


def sort_by_time(exp_id, experiments):
    date_time_str = experiments[exp_id]["started_ts"]
    return pendulum.parse(date_time_str)


def get_observed_throughput_of_last_experiment(
    minimum_current_ts: pendulum.DateTime,
) -> float:
    from ..g import g
    import logging
    url = getenv("PROMETHEUS_URL")
    prom = PrometheusConnect(url=url)

    # Get the most recent experiment
    experiments = {exp.doc_id: exp for exp in g.storage.experiments.all()}

    # Since we are using VictoriaMetrics, there's an additional flush required
    requests.get(f"{url}/internal/force_flush")

    # Filter experiments that started after the minimum_current_ts
    valid_experiments = {
        exp_id: exp
        for exp_id, exp in experiments.items()
        if pendulum.parse(exp["started_ts"]) >= minimum_current_ts
    }

    if not valid_experiments:
        breakpoint()
        print(f"No experiments found after {minimum_current_ts}")
        return float("NaN")

    latest_exp_id = max(
        valid_experiments.keys(),
        key=lambda x: pendulum.parse(valid_experiments[x]["started_ts"]),
    )
    latest_exp = valid_experiments[latest_exp_id]

    # Extract timestamps
    started_ts = pendulum.parse(latest_exp["started_ts"])
    stopped_ts = pendulum.parse(latest_exp["stopped_ts"])

    # Sanity check
    if started_ts < minimum_current_ts:
        print(
            f"Warning: Latest experiment started at {started_ts}, which is before the minimum timestamp {minimum_current_ts}"
        )
        return float("NaN")

    # Determine the namespace
    namespace = "redpanda" if "redpanda" in latest_exp["exp_name"] else "default"

    # Construct the query
    query = f'kminion_kafka_topic_high_water_mark_sum{{namespace="{namespace}", topic_name="input", experiment_started_ts="{latest_exp["started_ts"]}"}}'

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
            duration = latest_exp["experiment_metadata"]["factors"]["exp_params"][
                "durationSeconds"
            ]
        except KeyError:
            pass

        observed_throughput = max_watermark / duration

        logging.warning({"observed_throughput": observed_throughput})
        return observed_throughput

    except KeyError:
        print("No data found for the latest experiment")
        raise


def process_experiment(exp: Document) -> dict[str, Any]:
    metadata = exp["experiment_metadata"]
    params = metadata["factors"]["exp_params"]

    # Parse experiment description parameters first
    desc_params = {}
    if "experiment_description" in exp:
        desc_parts = exp["experiment_description"].split()
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
        "bw",
        "broker_replicas",
        "cluster",
    ]

    result = {
        "exp_id": exp.doc_id,
        "exp_name": exp["exp_name"],
        "started_ts": exp["started_ts"],
        "stopped_ts": exp["stopped_ts"],
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

    return {
        **result,
        **filtered_params,
    }


def filter_experiments(
    experiments: dict[int, Document],
    filter_condition: Callable[[Document], bool],
    *,
    cutoff_begin: str,
    cutoff_end: str,
) -> pd.DataFrame:
    cutoff_begin_date = pendulum.parse(cutoff_begin)
    cutoff_end_date = pendulum.parse(cutoff_end)

    filtered_experiments = [
        process_experiment(exp)
        for exp in sorted(
            experiments.values(),
            key=lambda x: pendulum.parse(x["started_ts"]),
            reverse=True,
        )
        if pendulum.parse(exp["started_ts"]) >= cutoff_begin_date
        and cutoff_end_date >= pendulum.parse(exp["started_ts"])
        and filter_condition(exp)
    ]

    return pd.DataFrame(filtered_experiments).set_index("exp_id")


def interest(*, cluster=None, type=None, exp_name=None, **kwargs) -> Callable[[Any], bool]:
    def _interest(exp):
        params = exp["experiment_metadata"]["factors"]["exp_params"]
        for k, v in params.items():
            if k in kwargs:
                if kwargs[k] != v:
                    return False
        if exp_name and exp_name not in exp["exp_name"]:
            return False
        if type and f"{type}=true" not in exp["experiment_description"]:
            return False
        if cluster and f"cluster={cluster}" not in exp["experiment_description"]:
            return False
        return True

    return _interest
