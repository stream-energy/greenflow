import logging
from kr8s.objects import Job
import pendulum

from entrypoint import rebind_parameters

from ..g import g
from ..state import get_deployment_state_vars, get_experiment_state_vars
from ..factors import factors
from ..exp_ng.exp_ng import *
from ..analysis import get_observed_throughput_of_last_experiment

bash_script_content = """
#!/bin/bash

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --topic)
                TOPIC="$2"
                shift 2
                ;;
            --num-records)
                NUM_RECORDS="$2"
                shift 2
                ;;
            --record-size)
                RECORD_SIZE="$2"
                shift 2
                ;;
            --producer-props)
                PRODUCER_PROPS="$2"
                shift 2
                ;;
            --start-timestamp)
                START_TIMESTAMP="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Parse command line arguments
parse_args "$@"

# Validate required parameters
if [[ -z "$TOPIC" || -z "$NUM_RECORDS" || -z "$RECORD_SIZE" || -z "$PRODUCER_PROPS" || -z "$START_TIMESTAMP" ]]; then
    echo "Missing required parameters. Usage:"
    echo "./synchronized_kafka_perf_test.sh --topic <topic> --num-records <num> --record-size <size> --producer-props <props> --start-timestamp <unix_timestamp>"
    exit 1
fi

# Wait until the specified start time
CURRENT_TIME=$(date +%s)
if [ "$START_TIMESTAMP" -gt "$CURRENT_TIME" ]; then
    SLEEP_DURATION=$((START_TIMESTAMP - CURRENT_TIME))
    echo "Waiting for $SLEEP_DURATION seconds before starting the test..."
    sleep $SLEEP_DURATION
else
    echo "Warning: Start time is in the past. Starting immediately."
fi

# Log the actual start time
ACTUAL_START_TIME=$(date +%s)
echo "Test started at: $ACTUAL_START_TIME"

# Run the Kafka producer performance test
kafka-producer-perf-test \
    --topic "$TOPIC" \
    --num-records "$NUM_RECORDS" \
    --record-size "$RECORD_SIZE" \
    --throughput -1 \
    --producer-props "$PRODUCER_PROPS" \
    --print-metrics

# Capture the exit status of the performance test
TEST_EXIT_STATUS=$?

# Log the end time
END_TIME=$(date +%s)
echo "Test ended at: $END_TIME"

# Calculate and print the total duration
DURATION=$((END_TIME - ACTUAL_START_TIME))
echo "Total test duration: $DURATION seconds"

# Exit with the status of the performance test
exit $TEST_EXIT_STATUS

"""

def exp_hammer_job(extra_vars) -> Job:
    exp_params = extra_vars["exp_params"]
    total_messages = 1 * 10**9
    start_timestamp = int(time.time()) + 20  # 20 seconds in the future


    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "kafka-producer-perf-test", "namespace": "default"},
            spec={
                "parallelism": exp_params["instances"],
                "completions": exp_params["instances"],
                "backoffLimit": 0,
                # "ttlSecondsAfterFinished": 100,
                "template": {
                    "metadata": {"labels": {"app": "kafka-producer-perf-test"}},
                    "spec": {
                        "restartPolicy": "Never",
                        "terminationGracePeriodSeconds": 0,
                        "nodeSelector": {"node.kubernetes.io/worker": "true"},
                        "containers": [
                            {
                                "name": "kafka-producer-perf-test",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/cp-kafka:7.7.0",
                                "imagePullPolicy": "IfNotPresent",
                                "command": [
                                    "/bin/sh",
                                    "-c",
                                    f"""
which kafka-producer-perf-test.sh
cat << 'EOF' > /tmp/synchronized_kafka_perf_test.sh
{bash_script_content}
EOF
chmod +x /tmp/synchronized_kafka_perf_test.sh
/tmp/synchronized_kafka_perf_test.sh \
    --topic input \
    --num-records {int(total_messages)} \
    --record-size {exp_params['messageSize']} \
    --producer-props bootstrap.servers={exp_params['kafka_bootstrap_servers']} \
    --start-timestamp {start_timestamp}
                                    """,
                                ],

                            }
                        ],
                    },
                },
            },
        )
    )

def deploy_hammer(extra_vars) -> Job:
    job = exp_hammer_job(extra_vars)
    # job = exp_job_custom(extra_vars)
    job.create()

    # Assume that it can take up to 20 seconds to start the job
    gracePeriod = 20
    totalDuration = extra_vars["exp_params"]["durationSeconds"] + gracePeriod

    try:
        job.wait(["condition=Complete", "condition=Failed"], timeout=totalDuration)
        if job.status.conditions[0].type == "Complete":
            job.delete(propagation_policy="Foreground")
            return
    except TimeoutError:
        # breakpoint()
        job.delete(propagation_policy="Foreground")
        return
    except KeyboardInterrupt:
        job.delete(propagation_policy="Foreground")
        return

def main():
    from pprint import pprint
    experiment_description = "Hammer"
    messageSize = 1024

    now = pendulum.now()
    g.init_exp(experiment_description)
    rebind_parameters(messageSize=messageSize)
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)

    reinit_prometheus(
        extra_vars["deployment_started_ts"], extra_vars["experiment_started_ts"]
    )
    create_kafka_topic(extra_vars)
    deploy_hammer(extra_vars)

    # Let the metrics get scraped before deleting the kafka topic
    time.sleep(15)
    scale_prometheus(0)

    delete_kafka_topic(extra_vars)
    g.end_exp()

    last_throughput = get_observed_throughput_of_last_experiment(minimum_current_ts=now)

    # logging.warning({"msg": "Hammer done", "last_throughput": last_throughput, "messageSize": messageSize})
