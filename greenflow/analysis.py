from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import pandas as pd
import pendulum
from greenflow.g import g
from tinydb import TinyDB, Query
from os import getenv

# Assuming your data is in the 'redpanda_kafka_data' DataFrame
import matplotlib.pyplot as plt
import seaborn as sns

url = getenv("PROMETHEUS_URL")
prom = PrometheusConnect(url=url)


def get_time_range(row: pd.Series, buffer_minutes: int = 1):
    started_ts = pendulum.parse(row["started_ts"]).subtract(minutes=buffer_minutes)
    stopped_ts = pendulum.parse(row["stopped_ts"]).add(minutes=buffer_minutes)
    return started_ts, stopped_ts


def calculate_throughput_MBps(row: pd.Series):
    """
    Calculate the throughput in megabytes per second (MBps).
    """
    message_size_bytes = row.get(
        "message_size_bytes", 1024
    )  # Default to 1KB if not specified
    observed_throughput_messages = row.get("observed_throughput", 0)

    mbps = (
        observed_throughput_messages * message_size_bytes / 1024 / 1024
    )  # Convert bytes to MBps

    row["throughput_MBps"] = mbps
    return row


def calculate_observed_throughput(row: pd.Series):
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f'kminion_kafka_topic_high_water_mark_sum{{namespace="{"redpanda" if "redpanda" in row["exp_name"] else "default"}", topic_name="input", experiment_started_ts="{row["started_ts"]}"}}'
    try:
        data = MetricRangeDataFrame(
            prom.get_metric_range_data(
                query,
                start_time=started_ts,
                end_time=stopped_ts,
            )
        )
    except KeyError:
        # Return the original row if no data is found
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

    throughput_gap_percentage = (throughput_gap / expected_throughput) * 100
    row["throughput_gap"] = throughput_gap
    row["throughput_gap_percentage"] = throughput_gap_percentage

    return row


def calculate_latency(row: pd.Series):
    started_ts, stopped_ts = get_time_range(row)

    query = f'histogram_quantile(0.99, sum(rate(kminion_end_to_end_produce_latency_seconds_bucket{{namespace="{"redpanda" if "redpanda" in row["exp_name"] else "default"}", experiment_started_ts="{row["started_ts"]}"}})) by (le))'
    try:
        data = prom.get_metric_range_data(
            query,
            start_time=started_ts.subtract(minutes=5),
            end_time=stopped_ts.add(minutes=5),
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

    # # Get the 99th percentile latency value
    # latency_p99 = data["value"].max()
    # row["latency_p99"] = latency_p99

    return row


def calculate_throughput_per_watt(row: pd.Series):
    """Use the average power consumption to calculate the throughput per watt"""
    throughput_per_watt = row["observed_throughput"] / row["average_power"]
    row["throughput_per_watt"] = throughput_per_watt

    return row


def calculate_average_power(row: pd.Series):
    """
    sum(scaph_host_power_microwatts{experiment_started_ts="$Experiment"}[5s]) / 10^6
    """
    # started_ts, stopped_ts = get_time_range(row)

    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f'sum(scaph_host_power_microwatts{{experiment_started_ts="{row["started_ts"]}"}}) / 10^6'
    # if started_ts < pendulum.now().subtract(hours=4):
    #     print(query, started_ts, stopped_ts)
    try:
        data = prom.custom_query_range(
            query,
            start_time=started_ts.subtract(minutes=1),
            end_time=stopped_ts.add(minutes=1),
            step="5s",
            # params={"step": "5s"},
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
    # Calculate observed throughput for each row
    df = df.apply(calculate_observed_throughput, axis=1)

    # Calculate throughput gap for each row
    df = df.apply(calculate_throughput_gap, axis=1)

    df = df.apply(calculate_latency, axis=1)
    df = df.apply(calculate_average_power, axis=1)

    return df
