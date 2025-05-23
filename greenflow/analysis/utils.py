from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import pandas as pd
import pendulum
from tinydb import TinyDB, Query
from os import getenv

from .tiny import get_experiments
from .tiny import filter_experiments
from .tiny import interest
from .cache import cache


import matplotlib.pyplot as plt
import seaborn as sns

url = getenv("PROMETHEUS_URL")
prom = PrometheusConnect(url=url)


def get_observed_throughput_of_last_experiment(
    minimum_current_ts: pendulum.DateTime,
) -> float:
    import greenflow

    if greenflow.g.g.storage_type == "tinydb":
        from .tiny import get_observed_throughput_of_last_experiment

        return get_observed_throughput_of_last_experiment(minimum_current_ts)
    elif greenflow.g.g.storage_type == "mongo":
        from .mongo import get_observed_throughput_of_last_experiment

        return get_observed_throughput_of_last_experiment(minimum_current_ts)


def full_analytical_pipeline_nocache(
    *,
    cutoff_begin=None,
    cutoff_end=None,
    cluster=None,
    type=None,
    **kwargs,
):
    import greenflow

    if not cutoff_begin:
        cutoff_begin = pendulum.now().subtract(years=1).to_iso8601_string()
    if not cutoff_end:
        cutoff_end = pendulum.now().to_iso8601_string()

    if greenflow.g.g.storage_type == "tinydb":
        experiments = get_experiments()
        redpanda_kafka_data = filter_experiments(
            experiments,
            interest(cluster=cluster, type=type, **kwargs),
            cutoff_begin=cutoff_begin,
            cutoff_end=cutoff_end,
        )
        redpanda_kafka_data = enrich_dataframe(redpanda_kafka_data)
        return redpanda_kafka_data
    else:
        from ..g import g
        from ..mongo_storage import ExpStorage, Experiment

        storage: ExpStorage = g.storage
        query = {
            "experiment_description": {
                "$regex": f"(?=.*type={type})(?=.*cluster={cluster})"
            },
            "started_ts": {"$gte": cutoff_begin, "$lte": cutoff_end},
            "experiment_metadata.results.duration": {"$gte": 100, "$lte": 3600},
        }

        for k, v in kwargs.items():
            query[f"experiment_metadata.factors.exp_params.{k}"] = v

        matching_experiments = storage.collection.find(
            query,
            sort=[("started_ts", -1)],
            # limit=1,
        ).to_list()

        # Get all _ids from matching experiments
        all_ids = [exp_doc["_id"] for exp_doc in matching_experiments]

        # Perform a batch query to get _ids that already have enriched results
        existing_results = storage.results_collection.find(
            {"_id": {"$in": all_ids}}, {"_id": 1}  # Project only the _id field
        ).to_list(None)

        # Extract the _ids of experiments that already have enriched results
        enriched_ids = {result["_id"] for result in existing_results}

        # Identify experiments that need to be enriched
        ids_to_enrich = set(all_ids) - enriched_ids

        # Filter experiments to enrich
        experiments_to_enrich = [
            exp_doc
            for exp_doc in matching_experiments
            if exp_doc["_id"] in ids_to_enrich
        ]

        # List to store all enriched experiments (existing and newly enriched)
        all_enriched_experiments = []

        # Retrieve existing enriched results
        existing_enriched_results = storage.results_collection.find(
            {"_id": {"$in": list(enriched_ids)}}
        ).to_list(None)

        # Add existing enriched results to the list
        all_enriched_experiments.extend(existing_enriched_results)

        # Enrich and store new results
        for exp_doc in experiments_to_enrich:
            exp_id = exp_doc["_id"]

            # Enrich the experiment data
            experiment = Experiment.from_doc(exp_doc)
            exp_dict = experiment.to_dict()
            df = pd.DataFrame([exp_dict])
            df["_id"] = exp_id  # Include the _id field
            df.set_index("_id", inplace=True)
            enriched_df = enrich_dataframe(df)

            # Convert the enriched dataframe back to a dictionary
            enriched_data = enriched_df.reset_index().iloc[0].to_dict()

            # Ensure that the _id field is correctly set
            enriched_data["_id"] = exp_id

            # Handle non-serializable data (convert ObjectId to string if necessary)
            enriched_data_serializable = ensure_serializable(enriched_data)

            # Remove _id from the update data since it's immutable
            if "_id" in enriched_data_serializable:
                del enriched_data_serializable["_id"]

            # Use update_one with upsert=True instead of insert_one
            storage.results_collection.update_one(
                {"_id": exp_id},  # filter
                {"$set": enriched_data_serializable},  # update (without _id field)
                upsert=True,  # create if doesn't exist
            )

            # Add to the list of all enriched experiments
            all_enriched_experiments.append(enriched_data)

        # Convert the list of all enriched experiments to a dataframe
        redpanda_kafka_data = pd.DataFrame(all_enriched_experiments)
        redpanda_kafka_data.set_index("_id", inplace=True)

        return redpanda_kafka_data
        # listExperiment = [Experiment.from_doc(exp) for exp in matching_experiments]
        # filtered_experiments = [exp.to_dict() for exp in listExperiment]


# @cache.pyarrow_cache
# def full_analytical_pipeline(
#     *,
#     cutoff_begin,
#     cutoff_end,
#     cluster=None,
#     type=None,
#     **kwargs,
# ):
#     return full_analytical_pipeline_nocache(
#         cutoff_begin=cutoff_begin,
#         cutoff_end=cutoff_end,
#         cluster=cluster,
#         type=type,
#         **kwargs,
#     )
full_analytical_pipeline = full_analytical_pipeline_nocache


def get_time_range(row: pd.Series, buffer_minutes: int = 1):
    started_ts = pendulum.parse(row["started_ts"]).subtract(minutes=buffer_minutes)
    stopped_ts = pendulum.parse(row["stopped_ts"]).add(minutes=buffer_minutes)
    return started_ts, stopped_ts


def calculate_network_saturation(row: pd.Series):
    """Calculate the average network saturation during the experiment duration"""
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f"""
    max_over_time(
    max(
        max by (device, node) (
        (
            irate(node_network_receive_bytes_total{{device=~"e.*", experiment_started_ts="{row['started_ts']}"}}[15s])
        )
        / on(device, node)
        (node_network_speed_bytes{{device=~"e.*", experiment_started_ts="{row['started_ts']}"}})
        )
    )[1m]
    )
    """

    try:
        data = prom.custom_query_range(
            query,
            start_time=started_ts,
            end_time=stopped_ts,
            step="5s",
        )
        data = MetricRangeDataFrame(data)
    except KeyError:
        row["network_saturation"] = float("NaN")
        return row

    if not data.empty:
        # Calculate the average network saturation
        network_saturation = data["value"].max()
        row["network_saturation"] = network_saturation
    else:
        row["network_saturation"] = float("NaN")

    return row


def calculate_disk_throughput(row: pd.Series):
    """Calculate the average disk throughput (MBps) during the experiment duration"""
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f"""
    max_over_time(
    sum(
        irate(node_disk_read_bytes_total{{device=~"nvme.*|sd.*", experiment_started_ts="{row['started_ts']}"}}[15s]) +
        irate(node_disk_written_bytes_total{{device=~"nvme.*|sd.*", experiment_started_ts="{row['started_ts']}"}}[15s])
    )[1m]
    )
    """

    try:
        data = prom.custom_query_range(
            query,
            start_time=started_ts,
            end_time=stopped_ts,
            step="5s",
        )
        data = MetricRangeDataFrame(data)
    except KeyError:
        row["disk_throughput_MBps"] = float("NaN")
        return row

    if not data.empty:
        # Calculate the maximum disk throughput and convert to MBps
        disk_throughput = data["value"].max() / (1024 * 1024)
        row["disk_throughput_MBps"] = disk_throughput
    else:
        row["disk_throughput_MBps"] = float("NaN")

    return row


def calculate_disk_utilization(row: pd.Series):
    """Calculate the disk utilization (percentage of time the device was busy)"""
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f"""
    max(
        rate(node_disk_written_bytes_total{{device=~"nvme.*|sd.*", experiment_started_ts="{row['started_ts']}"}}[1m])
    )
    """

    try:
        data = prom.custom_query_range(
            query,
            start_time=started_ts,
            end_time=stopped_ts,
            step="5s",
        )
        data = MetricRangeDataFrame(data)
    except KeyError:
        row["disk_utilization"] = float("NaN")
        return row

    if not data.empty:
        # Calculate the maximum disk utilization (as a fraction)
        disk_utilization = data["value"].mean()
        row["disk_utilization"] = disk_utilization
    else:
        row["disk_utilization"] = float("NaN")

    return row


# TODO: Add CPU
# 100 - (avg by (node) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)


def create_qgrid_widget(df: pd.DataFrame):
    import qgridnext as qgrid

    qgrid_widget = qgrid.show_grid(df, show_toolbar=True)
    return qgrid_widget


def calculate_observed_throughput(row: pd.Series):
    started_ts = pendulum.parse(row["started_ts"])
    stopped_ts = pendulum.parse(row["stopped_ts"])

    query = f'kminion_kafka_topic_high_water_mark_sum{{namespace="{"redpanda" if "redpanda" in row["exp_name"] else "default"}", topic_name="input", experiment_started_ts="{row["started_ts"]}"}}'
    if row.load == 0:
        return row
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
        breakpoint()
        return row

    # get the highest watermark using max- Represents the number of messages in the partition
    max_watermark = data["value"].max()
    duration = (stopped_ts - started_ts).total_seconds()
    duration = row["durationSeconds"] if "durationSeconds" in row else duration

    observed_throughput = max_watermark / duration

    row["observed_throughput"] = observed_throughput

    return row


def calculate_throughput_MBps(row: pd.Series):
    """
    Calculate the throughput in megabytes per second (MBps).
    """
    messageSize_bytes = row.get("messageSize", 0)
    observed_throughput_messages = row.get("observed_throughput", 0)

    mbps = (
        observed_throughput_messages * messageSize_bytes / 1024 / 1024
    )  # Convert bytes to MBps

    row["throughput_MBps"] = mbps
    row["adjusted_network_throughput"] = row["throughput_MBps"] * 1.45
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
    throughput_per_watt = row["throughput_MBps"] / row["average_power"]
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
        row["average_unit_power"] = average_power / row["broker_replicas"]
    else:
        row["average_power"] = 0

    return row


def calculate_energy_cost(row: pd.Series):
    """
    Calculate the energy cost in USD
    """
    if row["throughput_MBps"] == 0:
        row["energy_cost"] = 0
        return row
    # idle_power = 0
    if row.cluster == "taurus":
        if row.exp_name == "ingest-redpanda":
            idle_power_base = 31.63
        elif row.exp_name == "ingest-kafka":
            idle_power_base = 32.63
    elif row.cluster == "grappe":
        if row.exp_name == "ingest-redpanda":
            idle_power_base = 115.5 / 3
        elif row.exp_name == "ingest-kafka":
            idle_power_base = 123.87 / 3
    elif row.cluster == "ovhnvme":
        if row.exp_name == "ingest-redpanda":
            idle_power_base = 19.9
        elif row.exp_name == "ingest-kafka":
            idle_power_base = 20.5
    elif row.cluster == "ecotype":
        idle_power_base = 28.3
    elif row.cluster == "parasilo":
        idle_power_base = 28.3
    elif row.cluster == "parasilohdd":
        idle_power_base = 28.3
    else:
        idle_power_base = 0

    idle_power = idle_power_base * (row.num_broker_nodes - row.broker_replicas)

    row["adjusted_power"] = row["average_power"] - idle_power
    if row.average_power < 0:
        breakpoint()
        row["energy_cost"] = 0
        return row
    energy_cost = row["adjusted_power"] / row["throughput_MBps"]
    # energy_cost = 1 / energy_cost
    row["energy_cost"] = energy_cost

    return row


def convert_broker_cpu(row: pd.Series):
    """Convert the broker cpu from a string to an integer"""
    try:
        row["broker_cpu"] = int(row["broker_cpu"])
        return row
    except:
        return row


def enrich_dataframe(df):
    calculations = [
        calculate_observed_throughput,
        calculate_latency,
        calculate_average_power,
        calculate_throughput_MBps,
        # calculate_disk_throughput,
        # calculate_disk_utilization,
        # calculate_throughput_per_watt,
        calculate_energy_cost,
        calculate_network_saturation,
        calculate_throughput_gap,
        # convert_broker_cpu,
    ]

    for calc in calculations:
        try:
            # Process one calculation at a time
            # print(f"Running calculation: {calc.__name__}")
            df = df.apply(lambda row: safe_calculate(row, calc), axis=1)
        except Exception as e:
            print(f"Error in calculation {calc.__name__}: {str(e)}")

    return df


def safe_calculate(row, calculation):
    try:
        return calculation(row)
    except Exception as e:
        print(f"Error in row {row.name} for {calculation.__name__}:")
        print(f"Error message: {str(e)}")
        print("Row data:")
        print(row.to_dict())
        # Return the original row unchanged
        return row


def ensure_serializable(data):
    """Ensure that all data is serializable before storing in MongoDB."""
    import json
    from bson import ObjectId

    def convert_value(value):
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, float) and (pd.isna(value) or pd.isnull(value)):
            return None
        elif isinstance(value, (pd.Timestamp, pendulum.DateTime)):
            return value.isoformat()
        elif isinstance(value, dict):
            return ensure_serializable(value)
        elif isinstance(value, list):
            return [convert_value(v) for v in value]
        else:
            return value

    return {k: convert_value(v) for k, v in data.items()}
