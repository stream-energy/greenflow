from typing import Any, Callable
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import pandas as pd
import pendulum
import requests
from tinydb.table import Document
from tinydb import TinyDB, Query
from os import getenv

# Assuming your data is in the 'redpanda_kafka_data' DataFrame
import matplotlib.pyplot as plt
import seaborn as sns

def get_prometheus_url() -> str:
    url = getenv("PROMETHEUS_URL")
    return url

def get_prometheus(env: str = "test") -> PrometheusConnect:
    prom: PrometheusConnect = PrometheusConnect(url=get_prometheus_url())
    return prom

def get_experiments():
    from entrypoint import patch_global_g
    g = patch_global_g("test")
    experiments = {exp.doc_id: exp for exp in g.storage.experiments.all()}
    return experiments

def sort_by_time(exp_id, experiments):
    date_time_str = experiments[exp_id]["started_ts"]
    return pendulum.parse(date_time_str)

def get_observed_throughput_of_last_experiment(minimum_current_ts: pendulum.DateTime, prom=get_prometheus()) -> float:
    from .g import g
    import logging
    # Get the most recent experiment
    experiments = {exp.doc_id: exp for exp in g.storage.experiments.all()}

    # Since we are using VictoriaMetrics, there's an additional flush required
    requests.get(
        f"{get_prometheus_url()}/internal/force_flush"
    )

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
            prom.custom_query_range(
                query,
                start_time=started_ts,
                end_time=stopped_ts,
                step="5s",
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

def filter_experiments(
    experiments: dict[int, Document],
    filter_condition: Callable[[Document], bool],
    cutoff: str,
) -> pd.DataFrame:
    cutoff_date = pendulum.parse(cutoff)

    def is_valid_experiment(exp: Document) -> bool:
        return (pendulum.parse(exp["started_ts"]) >= cutoff_date) and filter_condition(
            exp
        )

    filtered_experiments = [
        process_experiment(exp)
        for exp in sorted(
            experiments.values(),
            key=lambda x: pendulum.parse(x["started_ts"]),
            reverse=True,
        )
        if pendulum.parse(exp["started_ts"]) >= cutoff_date and filter_condition(exp)
    ]

    return pd.DataFrame(filtered_experiments).set_index("exp_id")

def process_experiment(exp: Document) -> dict[str, Any]:
    metadata = exp["experiment_metadata"]
    params = metadata["factors"]["exp_params"]
    relevant_params = ["load", "durationSeconds", "messageSize"]
    filtered_params = {k: v for k, v in params.items() if k in relevant_params}

    return {
        "exp_id": exp.doc_id,
        "exp_name": exp["exp_name"],
        # "exp_description": exp["experiment_description"],
        "started_ts": exp["started_ts"],
        "stopped_ts": exp["stopped_ts"],
        **metadata.get("results", {}),
        **filtered_params,
    }

def get_time_range(row: pd.Series, buffer_minutes: int = 1):
    started_ts = pendulum.parse(row["started_ts"]).subtract(minutes=buffer_minutes)
    stopped_ts = pendulum.parse(row["stopped_ts"]).add(minutes=buffer_minutes)
    return started_ts, stopped_ts

def calculate_throughput_MBps(row: pd.Series):
    """
    Calculate the throughput in megabytes per second (MBps).
    """
    messageSize_bytes = row.get(
        "messageSize", 1024
    )  # Default to 1KB if not specified
    observed_throughput_messages = row.get("observed_throughput", 0)

    mbps = (
        observed_throughput_messages * messageSize_bytes / 1024 / 1024
    )  # Convert bytes to MBps

    row["throughput_MBps"] = mbps
    return row

def calculate_observed_throughput(row: pd.Series, prom=get_prometheus()):
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f'kminion_kafka_topic_high_water_mark_sum{{namespace="{"redpanda" if "redpanda" in row["exp_name"] else "default"}", topic_name="input", experiment_started_ts="{row["started_ts"]}"}}'
    try:
        data = MetricRangeDataFrame(
            prom.custom_query_range(
                query,
                start_time=started_ts,
                end_time=stopped_ts,
                step="5s",
            )
        )
    except KeyError:
        # Return the original row if no data is found
        breakpoint()
        return row

    # get the highest watermark using max- Represents the number of messages in the partition
    max_watermark = data["value"].max()
    duration = (stopped_ts - started_ts).total_seconds()
    duration = row["durationSeconds"] if "durationSeconds" in row else duration

    observed_throughput = max_watermark / duration

    row["observed_throughput"] = observed_throughput

    return row

def calculate_throughput_gap(row: pd.Series):
    expected_throughput = float(row["load"])
    try:
        throughput_gap = row["observed_throughput"] - expected_throughput
    except KeyError:
        throughput_gap = float("NaN")

    try:
        throughput_gap_percentage = (throughput_gap / expected_throughput) * 100
    except ZeroDivisionError:
        throughput_gap_percentage = float("NaN")
    # row["throughput_gap"] = throughput_gap
    row["throughput_gap_percentage"] = throughput_gap_percentage

    return row

def calculate_latency(row: pd.Series, prom=get_prometheus()):
    started_ts, stopped_ts = get_time_range(row)

    query = f'histogram_quantile(0.99, sum(rate(kminion_end_to_end_produce_latency_seconds_bucket{{namespace="{"redpanda" if "redpanda" in row["exp_name"] else "default"}", experiment_started_ts="{row["started_ts"]}"}})) by (le))'
    try:
        data = prom.custom_query_range(
            query,
            start_time=started_ts.subtract(minutes=5),
            end_time=stopped_ts.add(minutes=5),
            step="5s",
        )
        data = MetricRangeDataFrame(data)
    except KeyError:
        return row

    data = data[data["value"].notna()]

    if not data.empty:
        # Get the 99th percentile latency value
        latency_p99 = data["value"].max()
        row["latency_p99"] = latency_p99
    else:
        row["latency_p99"] = 0

    return row

def calculate_throughput_per_watt(row: pd.Series):
    """Use the average power consumption to calculate the throughput per watt"""
    throughput_per_watt = row["throughput_MBps"] / row["average_power"]
    row["throughput_per_watt"] = throughput_per_watt

    return row

def calculate_average_power(row: pd.Series, prom=get_prometheus()):
    """
    sum(scaph_host_power_microwatts{experiment_started_ts="$Experiment"}[5s]) / 10^6
    """
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f'sum(scaph_host_power_microwatts{{experiment_started_ts="{row["started_ts"]}"}}) / 10^6'
    try:
        data = prom.custom_query_range(
            query,
            start_time=started_ts.subtract(minutes=1),
            end_time=stopped_ts.add(minutes=1),
            step="5s",
        )
        data = MetricRangeDataFrame(data)
    except KeyError:
        row["average_power"] = float("NaN")
        return row

    if not data.empty:
        # Calculate the average power consumption
        average_power = data["value"].mean()
        row["average_power"] = average_power
    else:
        row["average_power"] = 0

    return row

def enrich_dataframe(df):
    calculations = [
        calculate_observed_throughput,
        calculate_throughput_gap,
        # calculate_latency,
        calculate_average_power,
        calculate_throughput_MBps,
        calculate_throughput_per_watt,
    ]

    for calc in calculations:
        df = df.apply(calc, axis=1)

    return df
