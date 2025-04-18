import logging
from box import Box
from kr8s.objects import Job
import pendulum
import time
import numpy as np

from entrypoint import rebind_parameters
from .exp_ng import create_kafka_topic, delete_kafka_topic
from .prometheus import reinit_prometheus, scale_prometheus

from ..state import get_deployment_state_vars, get_experiment_state_vars
from ..factors import factors
from .synchronized_perf_script import producer_script, consumer_script


def exp_consumer_job(extra_vars) -> Job:
    exp_params = extra_vars["exp_params"]
    start_timestamp = int(time.time()) + 20  # 20 seconds in the future

    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "kafka-consumer-perf-test", "namespace": "default"},
            spec={
                "parallelism": exp_params["consumer_instances"],
                "completions": exp_params["consumer_instances"],
                "backoffLimit": 0,
                "template": {
                    "metadata": {"labels": {"app": "kafka-consumer-perf-test"}},
                    "spec": {
                        "restartPolicy": "Never",
                        "terminationGracePeriodSeconds": 0,
                        "nodeSelector": {"node.kubernetes.io/worker": "true"},
                        "containers": [
                            {
                                "name": "kafka-consumer-perf-test",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/cp-kafka:7.7.0",
                                "imagePullPolicy": "IfNotPresent",
                                "command": [
                                    "/bin/sh",
                                    "-c",
                                    f"""
cat << 'EOF' > /tmp/synchronized_kafka_consumer_test.sh
{consumer_script}
EOF
chmod +x /tmp/synchronized_kafka_consumer_test.sh
/tmp/synchronized_kafka_consumer_test.sh \
    --topic input \
    --bootstrap-server {exp_params['kafka_bootstrap_servers']} \
    --durationSeconds {exp_params['durationSeconds']} \
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


def deploy_hammer_with_consumer(extra_vars) -> tuple[Job, Job]:
    # producer_job = exp_hammer_job(extra_vars)
    producer_job = exp_perf_test_job(extra_vars) # Switching back to the original producer job
    consumer_job = exp_consumer_job(extra_vars)

    producer_job.create()
    consumer_job.create()

    # Assume that it can take up to 20 seconds to start the jobs
    gracePeriod = 20
    totalDuration = extra_vars["exp_params"]["durationSeconds"] + gracePeriod

    try:
        # Wait for both jobs to complete or fail
        producer_job.wait(
            ["condition=Complete", "condition=Failed"], timeout=totalDuration
        )
        consumer_job.wait(
            ["condition=Complete", "condition=Failed"], timeout=totalDuration
        )

        cleanup_jobs = True
        if (
            producer_job.status.conditions[0].type == "Complete"
            and consumer_job.status.conditions[0].type == "Complete"
        ):
            cleanup_jobs = True
    except TimeoutError:
        cleanup_jobs = True
    except KeyboardInterrupt:
        cleanup_jobs = True
    finally:
        if cleanup_jobs:
            producer_job.delete(propagation_policy="Foreground")
            consumer_job.delete(propagation_policy="Foreground")

def exp_perf_test_job(extra_vars) -> Job:
    # TODO: Merge this with normal job
    extra_vars = Box(extra_vars)
    exp_params = extra_vars.exp_params
    load = exp_params.load / exp_params.producer_instances
    total_messages = load * exp_params.durationSeconds
    producer_instances = exp_params.producer_instances
    start_timestamp = int(time.time()) + 20  # 20 seconds in the future
    if load == 1 * 10**9:
        throughput = -1
    else:
        throughput = int(load)

    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "kafka-producer-perf-test", "namespace": "default"},
            spec={
                "parallelism": producer_instances,
                "completions": producer_instances,
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
                                "resources": {
                                    "requests": {
                                        "cpu": "2000m",
                                        "memory": "2Gi"
                                    },
                                    "limits": {
                                        "cpu": "2000m",
                                        "memory": "2Gi"
                                    }
                                },
                                "command": [
                                    "/bin/sh",
                                    "-c",
                                    f"""
cat << 'EOF' > /tmp/synchronized_kafka_perf_test.sh
{producer_script}
EOF
chmod +x /tmp/synchronized_kafka_perf_test.sh
/tmp/synchronized_kafka_perf_test.sh \
    --topic input \
    --num-records {int(total_messages)} \
    --record-size {exp_params.messageSize} \
    --throughput {throughput} \
    --bootstrap-servers {exp_params.kafka_bootstrap_servers} \
    --producer-props "batch.size=32768" \
    --durationSeconds {exp_params.durationSeconds} \
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



def exp_hammer_job(extra_vars) -> Job:
    exp_params = extra_vars["exp_params"]
    total_messages = int(
        exp_params["load"]
        * exp_params["durationSeconds"]
        / exp_params["producer_instances"]
    )
    start_timestamp = int(time.time()) + 15

    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "kafka-producer-perf-test", "namespace": "default"},
            spec={
                "parallelism": exp_params.producer_instances,
                "completions": exp_params.producer_instances,
                "backoffLimit": 0,
                # "ttlSecondsAfterFinished": 100,
                "template": {
                    "metadata": {"labels": {"app": "kafka-producer-perf-test"}},
                    "spec": {
                        "restartPolicy": "Never",
                        "terminationGracePeriodSeconds": 0,
                        "nodeSelector": {"node.kubernetes.io/worker": "true"},

                        # "affinity": {
                        #     "podAntiAffinity": {
                        #         "requiredDuringSchedulingIgnoredDuringExecution": [
                        #             {
                        #                 "labelSelector": {
                        #                     "matchExpressions": [
                        #                         {
                        #                             "key": "app",
                        #                             "operator": "In",
                        #                             "values": [
                        #                                 "kafka-producer-perf-test"
                        #                             ],
                        #                         }
                        #                     ]
                        #                 },
                        #                 "topologyKey": "kubernetes.io/hostname",
                        #             }
                        #         ]
                        #     }
                        # },
                        "containers": [
                            {
                                "name": "kafka-producer-perf-test",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/throughput",
                                "imagePullPolicy": "Always",
                                # "resources": {
                                #     "requests": {
                                #         "cpu": "4",
                                #         "memory": "4Gi"
                                #     },
                                #     "limits": {
                                #         "cpu": "4",
                                #         "memory": "4Gi"
                                #     }
                                # },
                                "env": [
                                    {
                                        "name": "THROUGHPUT_BROKERS",
                                        "value": exp_params.kafka_bootstrap_servers,
                                    },
                                    {
                                        "name": "THROUGHPUT_MESSAGE_SIZE",
                                        "value": str(exp_params.messageSize),
                                    },
                                    {
                                        "name": "THROUGHPUT_DURATION",
                                        "value": f"{exp_params.durationSeconds}s",
                                    },
                                    {
                                        "name": "THROUGHPUT_NUM_PRODUCERS",
                                        "value": "4",
                                    },
                                    {
                                        "name": "THROUGHPUT_WORKERS_PER_PRODUCER",
                                        "value": "2",
                                    },
                                    {
                                        "name": "THROUGHPUT_START_TIMESTAMP",
                                        "value": str(start_timestamp),
                                    },
                                ],
                            }
                        ],
                    },
                },
            },
        )
    )


def hammer(experiment_description="Hammer") -> float:
    from pprint import pprint
    from ..g import g
    from ..analysis import get_observed_throughput_of_last_experiment
    from entrypoint import rebind_parameters

    now = pendulum.now()
    g.init_exp(experiment_description)
    rebind_parameters(load=1 * 10**9)
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)
    logging.warning(
        dict(
            msg="Hammering",
            messageSize=extra_vars.exp_params.messageSize,
            load=1 * 10**9,
        )
    )

    reinit_prometheus(
        extra_vars["deployment_started_ts"], extra_vars["experiment_started_ts"]
    )
    create_kafka_topic(extra_vars)
    deploy_hammer_with_consumer(extra_vars)
    # deploy_hammer(extra_vars)

    # Let the metrics get scraped before deleting the kafka topic
    time.sleep(15)
    scale_prometheus(0)

    delete_kafka_topic(extra_vars)
    g.end_exp()

    last_throughput = get_observed_throughput_of_last_experiment(minimum_current_ts=now)
    return last_throughput


def stress_test(target_load: float, exp_description="Stress Test") -> float:
    from pprint import pprint
    from ..g import g
    from ..analysis import get_observed_throughput_of_last_experiment

    # Convert target_load to standard Python float if it's a numpy float
    if isinstance(target_load, (np.floating, np.float32, np.float64)):
        target_load = target_load.item()
    else:
        target_load = float(
            target_load
        )  # Ensure it's a float even if passed as int/string

    rebind_parameters(load=target_load)

    now = pendulum.now()
    g.init_exp(exp_description)
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)

    logging.warning(
        dict(
            msg="Stress testing",
            messageSize=extra_vars.exp_params.messageSize,
            target_throughput=target_load,
        )
    )

    reinit_prometheus(
        extra_vars["deployment_started_ts"], extra_vars["experiment_started_ts"]
    )
    if target_load != 0:
        create_kafka_topic(extra_vars)

        deploy_hammer_with_consumer(extra_vars)

        # Let the metrics get scraped before deleting the kafka topic
        time.sleep(15)
        scale_prometheus(0)

        delete_kafka_topic(extra_vars)
        time.sleep(15)
        g.end_exp()
        time.sleep(15)

        last_throughput = get_observed_throughput_of_last_experiment(
            minimum_current_ts=now
        )
        return last_throughput
    else:
        time.sleep(extra_vars.exp_params.durationSeconds)
        scale_prometheus(0)
        g.end_exp()
