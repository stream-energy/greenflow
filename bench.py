import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Mapping
import argparse
from pathlib import Path

from kubernetes import config, client
from kubernetes.client import CoreV1Api, V1Pod

USED_NAMESPACE = "default"
BENCHMARK_POD_NAME = "benchmark-pod"


def create_benchmark_pod(core_v1: CoreV1Api) -> V1Pod:
    """
    Creates a benchmark Pod using the image defined in environment variable BENCHMARK_IMAGE.
    """
    image = os.getenv(
        "BENCHMARK_IMAGE", "ghcr.io/mshekow/pts-docker-benchmark:2023.12.15"
    )

    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": BENCHMARK_POD_NAME, "labels": {"app": "benchmark"}},
        "spec": {
            "containers": [{"image": image, "name": "benchmark"}],
            "restartPolicy": "Never",
        },
    }

    try:
        pod = core_v1.create_namespaced_pod(body=pod_manifest, namespace=USED_NAMESPACE)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logging.info(
                f"Replacing Pod {BENCHMARK_POD_NAME} because it already exists"
            )
            core_v1.delete_namespaced_pod(BENCHMARK_POD_NAME, USED_NAMESPACE)
            pod = core_v1.create_namespaced_pod(
                body=pod_manifest, namespace=USED_NAMESPACE
            )
        else:
            raise e
    return pod


RETRY_INTERVAL_SECONDS = 30
MAX_TIMEOUT_SECONDS = 90 * 60


def wait_for_pod_to_finish(core_v1: CoreV1Api, pod: V1Pod):
    """
    Waits until the pod has reached the "Succeeded" or "Failed" phase.
    If the Pod has reached the "Failed" phase, this method raises an exception.
    """
    for _ in range(MAX_TIMEOUT_SECONDS // RETRY_INTERVAL_SECONDS):
        pod_status = core_v1.read_namespaced_pod_status(
            pod.metadata.name, pod.metadata.namespace
        ).status.phase

        if pod_status in ["Succeeded", "Failed"]:
            if pod_status == "Failed":
                failed_pod_log = core_v1.read_namespaced_pod_log(
                    pod.metadata.name, pod.metadata.namespace
                )
                raise Exception(
                    f"Pod {pod.metadata.name} failed, logs:\n{failed_pod_log}"
                )
            break
        else:
            logging.info(
                f"Still waiting for Pod to complete, current status: {pod_status}"
            )

        time.sleep(RETRY_INTERVAL_SECONDS)

    logging.info("Benchmark pod has successfully completed")


@dataclass
class BenchmarkResult:
    tool_name: str
    tool_config: str
    result_unit: str
    result_value: str


MARKER_LINE = "benchmarkresult"


def extract_relevant_log_lines(pod_log: str, node_pool_name: str) -> list[str]:
    """
    Returns the last few lines of the provided Pod log that actually contain benchmark results.
    """
    log_lines = pod_log.splitlines(keepends=False)

    # Find the line that contains the MARKER_LINE
    marker_line_index = None
    for i, line in enumerate(log_lines):
        if line == MARKER_LINE:
            marker_line_index = i
            break
    if marker_line_index is None:
        raise ValueError(
            f"Unable to find the marker line '{MARKER_LINE}' in the '{node_pool_name}' Pod log"
        )

    if "testing" not in log_lines[marker_line_index + 1]:
        raise ValueError(
            f"Expected 'testing' line following the marker line in the '{node_pool_name}' Pod log, "
            f"but it is missing"
        )

    if log_lines[marker_line_index + 2] != "":
        raise ValueError(
            f"Expected empty line following the 'testing' line in the '{node_pool_name}' Pod log, "
            f"but it '{log_lines[marker_line_index + 2]}'"
        )

    # Find the next empty line that follows marker_line_index+2
    empty_line_index = None
    for i in range(marker_line_index + 3, len(log_lines)):
        if log_lines[i] == "":
            empty_line_index = i
            break
    if empty_line_index is None:
        raise ValueError(
            f"Unable to find the next empty line after the marker line '{MARKER_LINE}' in "
            f"the '{node_pool_name}' Pod log"
        )

    if "Disk" not in log_lines[empty_line_index + 1]:
        raise ValueError(
            f"Expected 'Disk' line in the '{node_pool_name}' Pod log, but it is missing"
        )

    relevant_log_lines = log_lines[empty_line_index + 2 :]
    return [line for line in relevant_log_lines if line != ""]


PTS_CSV_REGEX = re.compile(
    r"^\"(?P<testtool>.*) - (?P<testconfig>.*?)\((?P<resultunit>.*)\)\",(?P<hib>.*),(?P<resultvalue>.*)$"
)


def extract_benchmark_results_from_pod_log(pod_log: str) -> list[BenchmarkResult]:
    """
    Extracts the benchmark results from the provided Pod log.
    """
    benchmark_results = []
    relevant_lines = extract_relevant_log_lines(pod_log, BENCHMARK_POD_NAME)
    for line in relevant_lines:
        match = PTS_CSV_REGEX.search(line)
        if not match:
            raise ValueError(f"Unable to parse line '{line}' (regex failed)")

        test_tool = match.group("testtool")
        test_config = match.group("testconfig").strip()
        result_unit = match.group("resultunit")
        hib = match.group("hib")
        result_value = match.group("resultvalue")

        if hib != "HIB":
            raise ValueError(f"Invalid value '{hib}' in line '{line}' (expected 'HIB')")

        benchmark_results.append(
            BenchmarkResult(
                tool_name=test_tool,
                tool_config=test_config,
                result_unit=result_unit,
                result_value=result_value,
            )
        )

    return benchmark_results


def collect_benchmark_results(pod_log: str) -> str:
    """
    Given the pod log, this function returns a string that contains the parsed benchmark results in CSV format.
    """
    benchmark_results = extract_benchmark_results_from_pod_log(pod_log)

    result_lines = ["Tool name + config + result unit;Result"]
    for result in sorted(benchmark_results, key=lambda x: (x.tool_name, x.tool_config)):
        result_lines.append(
            f"{result.tool_name} - {result.tool_config} ({result.result_unit});{result.result_value}"
        )

    return "\n".join(result_lines)


def store_raw_logs(pod_log: str):
    """
    Stores the raw logs of the benchmark Pod.
    """
    os.makedirs("raw-results", exist_ok=True)
    result_folder_name = f"raw-results/{time.strftime('%Y-%m-%d-%H-%M')}"
    os.makedirs(result_folder_name, exist_ok=True)

    with open(f"{result_folder_name}/benchmark.log", "w") as f:
        f.write(pod_log)


def save_benchmark_logs(pod_log: str, output_dir: str = "benchmark_logs"):
    """
    Saves the raw benchmark logs to a timestamped file in the specified directory.
    Returns the path to the saved log file.
    """
    log_dir = Path(output_dir)
    log_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime('%Y-%m-%d-%H-%M')
    log_file = log_dir / f"benchmark-{timestamp}.log"
    
    with open(log_file, 'w') as f:
        f.write(pod_log)
    
    return log_file

def process_saved_log(log_file: Path) -> str:
    """
    Processes a previously saved benchmark log file and returns the CSV content.
    """
    with open(log_file, 'r') as f:
        pod_log = f.read()
    return collect_benchmark_results(pod_log)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    parser = argparse.ArgumentParser(description='Run or process kubernetes benchmarks')
    parser.add_argument('--mode', choices=['run', 'process'], default='run',
                       help='Run benchmark or process existing logs')
    parser.add_argument('--log-file', type=Path,
                       help='Log file to process (required if mode is process)')
    parser.add_argument('--output-dir', default='benchmark_logs',
                       help='Directory to save benchmark logs')
    args = parser.parse_args()

    if args.mode == 'run':
        config.load_kube_config()
        core_v1 = client.CoreV1Api()
        core_v1.list_node()  # Verify credentials

        if os.getenv("SKIP_POD_CREATION") == "true":
            pod = core_v1.read_namespaced_pod(BENCHMARK_POD_NAME, USED_NAMESPACE)
        else:
            pod = create_benchmark_pod(core_v1)

        wait_for_pod_to_finish(core_v1, pod)
        pod_log = core_v1.read_namespaced_pod_log(pod.metadata.name, pod.metadata.namespace)
        
        # Save the raw logs
        log_file = save_benchmark_logs(pod_log, args.output_dir)
        logging.info(f"Saved raw benchmark logs to {log_file}")
        
        # Process the logs
        csv_content = collect_benchmark_results(pod_log)
        
    elif args.mode == 'process':
        if not args.log_file:
            parser.error("--log-file is required when mode is 'process'")
        if not args.log_file.exists():
            parser.error(f"Log file {args.log_file} does not exist")
            
        csv_content = process_saved_log(args.log_file)

    # Save the CSV results
    with open("benchmark_results.csv", "w") as f:
        f.write(csv_content)
