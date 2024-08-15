# Data Analysis

This chapter provides an overview of how to analyze data collected from GreenFlow experiments. It includes a brief introduction to Prometheus querying with PromQL, and explains how to use the provided tools and scripts for data analysis.

## Overview of Prometheus and PromQL

Prometheus is a powerful monitoring and alerting toolkit that collects and stores metrics as time series data. PromQL (Prometheus Query Language) is used to query this data. Understanding the basics of PromQL is essential for effective data analysis.

### Prometheus Metrics

Prometheus metrics are stored with labels that provide additional context. A metric consists of:

- **Metric Name**: Describes the type of data being measured (e.g., `http_requests_total`).
- **Labels**: Key-value pairs that provide additional information about the metric (e.g., `method="GET"`).

### Basic PromQL Queries

- **Instant Vector**: A set of time series containing a single sample for each time series, all sharing the same timestamp.

```promql
http_requests_total
```

- **Range Vector**: A set of time series containing a range of data points over time.

```promql
http_requests_total[5m]
```

- **Aggregation**: Summarizes or groups data.

```promql
sum(http_requests_total) by (method)
```

For more detailed information, refer to the [Prometheus documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/).

## Data analysis in GreenFlow

GreenFlow provides tools and scripts to facilitate data analysis. The primary tools include the analysis.py script and Jupyter notebooks.

Since the metrics are stored in the VictoriaMetrics instance, they can be queried and accessed through filtering for `experiment_started_ts` to zoom in on a particular experiment. Make use of Grafana for exploring and visualizing the data.

### Analysis Script: analysis.py

The analysis.py script contains helper functions for performing various calculations and data manipulations using pandas DataFrames. This script is used to automate the data analysis process.
Key functions in analysis.py:

- get_experiments(): Retrieves experiment data.
- filter_experiments(): Filters experiments based on specified criteria.
- enrich_dataframe(): Adds additional computed columns to the DataFrame for analysis.

## Example Workflow in Jupyter Notebook

Below is an example workflow for analyzing data using a Jupyter notebook. This workflow includes steps for filtering experiments, enriching data, and creating visualizations.

```python
# %%
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import pandas as pd
import pendulum
from greenflow.g import g
from tinydb import TinyDB, Query
from os import getenv
import matplotlib.pyplot as plt
import seaborn as sns
import greenflow.analysis as an
import qgridnext as qgrid

# %%
# Retrieve and filter experiments
cutoff = "2024-07-23T14:40:18.761822+02:00"
experiments = an.get_experiments()

def interest(exp) -> bool:
  params = exp["experiment_metadata"]["factors"]["exp_params"]
  messageSize = params["messageSize"]
  partitions = params["partitions"]
  if "cluster=chirop" in exp["experiment_description"]:
    if messageSize > 64 and partitions >= 1:
      return True
  return False

redpanda_kafka_data = an.filter_experiments(experiments, interest, cutoff)

# %%
# Enrich data and visualize
enriched_data = an.enrich_dataframe(redpanda_kafka_data)
enriched_data = enriched_data[enriched_data["throughput_gap_percentage"] < 0]

# Create a scatter plot
def create_graph(data, system_name):
    fig, ax = plt.subplots(figsize=(12, 8))
    cmap = plt.cm.RdYlGn
    scatter = ax.scatter(
        data["messageSize"], data["load"], c=data["throughput_gap_percentage"], cmap=cmap, s=50
    )
    plt.colorbar(scatter, ax=ax, label="Throughput Gap (%)", extend="min")
    ax.set_title(f"Load vs Message Size for {system_name}")
    ax.set_xlabel("Message Size (bytes)")
    ax.set_ylabel("Load (messages/sec)")
    plt.tight_layout()
    plt.show()

# Create graphs for Kafka and Redpanda
create_graph(enriched_data[enriched_data["exp_name"] == "ingest-kafka"], "Kafka")
create_graph(enriched_data[enriched_data["exp_name"] == "ingest-redpanda"], "Redpanda")
```

## Custom Analysis

For custom analysis, you can modify the provided Jupyter notebook or create your own analysis scripts using the functions in analysis.py. The Jupyter notebook provides an interactive environment for exploring and visualizing data, while the analysis.py script offers reusable functions for common analysis tasks.
