import threading
import traceback
from kr8s.objects import Job
import time
from sh import kubectl
from shlex import split

from box import Box, BoxList

from .prometheus import reinit_prometheus, scale_prometheus

from ..factors import factors
from ..playbook import _playbook
from ..state import get_deployment_state_vars, get_experiment_state_vars


def create_job(extra_vars) -> Job:
    pushgateway_url = extra_vars["prometheus_pushgateway_url"]
    exp_params = extra_vars["exp_params"]

    # First, check if the topic exists
    check_topic_args = BoxList(
        [
            "topic",
            "describe",
            "input",
            "-X",
            f"brokers={exp_params.kafka_bootstrap_servers}",
        ]
    )

    create_topic_args = BoxList(
        [
            "topic",
            "create",
            "input",
            "-r",
            f"{exp_params.replicationFactor}",
            "-p",
            f"{exp_params.partitions}",
            "-X",
            f"brokers={exp_params.kafka_bootstrap_servers}",
        ]
        + (["-c", "write.caching=true"] if "redpanda" in extra_vars.exp_name else [])
    )

    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "create-kafka-topic", "namespace": "default"},
            spec={
                "backoffLimit": 0,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "create-topic",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/redpanda:v24.1.8",
                                "command": ["/bin/sh"],
                                "args": [
                                    "-c",
                                    f"""
                                    if rpk {' '.join(check_topic_args)} > /dev/null 2>&1; then
                                        echo "Topic 'input' already exists."
                                        exit 0
                                    else
                                        rpk {' '.join(create_topic_args)}
                                    fi
                                    """,
                                ],
                            }
                        ],
                    }
                },
            },
        )
    )




def exp_job_custom(extra_vars) -> Job:
    pushgateway_url = extra_vars["prometheus_pushgateway_url"]
    exp_params = extra_vars["exp_params"]
    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "throughput", "namespace": "default"},
            spec={
                "parallelism": exp_params["instances"],
                "completions": exp_params["instances"],
                "backoffLimit": 0,
                # "ttlSecondsAfterFinished": 5,
                "template": {
                    "metadata": {"labels": {"app": "throughput"}},
                    "spec": {
                        "restartPolicy": "Never",
                        "terminationGracePeriodSeconds": 0,
                        "nodeSelector": {"node.kubernetes.io/worker": "true"},
                        "containers": [
                            {
                                "name": "workload-generator",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/throughput",
                                "imagePullPolicy": "Always",
                                "env": [
                                    {
                                        "name": "THROUGHPUT_BROKERS",
                                        "value": exp_params["kafka_bootstrap_servers"],
                                    },
                                    {"name": "THROUGHPUT_TOPIC", "value": "input"},
                                    {
                                        "name": "THROUGHPUT_MESSAGE_RATE",
                                        "value": str(
                                            exp_params["load"]
                                            // exp_params["instances"]
                                        ),
                                    },
                                    {
                                        "name": "THROUGHPUT_DURATION",
                                        "value": f"{exp_params['durationSeconds']}s",
                                    },
                                    {
                                        "name": "THROUGHPUT_MESSAGE_SIZE",
                                        "value": str(exp_params["messageSize"]),
                                    },
                                    {
                                        "name": "THROUGHPUT_PUSHGATEWAY_URL",
                                        "value": pushgateway_url,
                                    },
                                ],
                            }
                        ],
                    },
                },
            },
        )
    )


def exp_job(extra_vars) -> Job:
    exp_params = extra_vars["exp_params"]
    total_messages = exp_params["load"] * exp_params["durationSeconds"]

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
                                    kafka-producer-perf-test \
                                        --topic input \
                                        --num-records {int(total_messages // exp_params['instances'])} \
                                        --record-size {exp_params['messageSize']} \
                                        --throughput {int(exp_params['load'] // exp_params['instances'])} \
                                        --producer-props bootstrap.servers={exp_params['kafka_bootstrap_servers']} \
                                        --print-metrics
                                    """,
                                ],
                            }
                        ],
                    },
                },
            },
        )
    )


def delete_job(extra_vars) -> Job:
    exp_params = extra_vars["exp_params"]
    return Job(
        dict(
            apiVersion="batch/v1",
            kind="Job",
            metadata={"name": "delete-kafka-topic", "namespace": "default"},
            spec={
                # "ttlSecondsAfterFinished": 5,
                "backoffLimit": 0,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "delete-topic",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/redpanda:v24.1.8",
                                "command": ["rpk"],
                                "args": [
                                    "topic",
                                    "delete",
                                    "input",
                                    "-X",
                                    f"brokers={exp_params.kafka_bootstrap_servers}",
                                ],
                            }
                        ],
                    }
                },
            },
        )
    )


def create_kafka_topic(extra_vars):
    job = create_job(extra_vars)
    job.create()
    job.wait(["condition=Complete", "condition=Failed"])
    if job.status.conditions[0].type == "Complete":
        job.delete(propagation_policy="Foreground")
        return
    else:
        raise RuntimeError("Failed to create kafka topic")


def deploy_experiment(extra_vars) -> Job:
    job = exp_job(extra_vars)
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


def delete_kafka_topic(extra_vars):
    job = delete_job(extra_vars)
    job.create()
    job.wait(["condition=Complete", "condition=Failed"])
    if job.status.conditions[0].type == "Complete":
        job.delete(propagation_policy="Foreground")
        return
    else:
        raise RuntimeError("Failed to delete kafka topic")


def exp(experiment_description):
    exp_name = factors()["exp_name"]
    from ..g import g

    g.init_exp(exp_name, experiment_description)
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)

    reinit_prometheus(
        extra_vars["deployment_started_ts"], extra_vars["experiment_started_ts"]
    )
    create_kafka_topic(extra_vars)
    deploy_experiment(extra_vars)

    # Let the metrics get scraped before deleting the kafka topic
    time.sleep(15)
    scale_prometheus(0)

    delete_kafka_topic(extra_vars)

    g.end_exp()


def killexp():
    from ..g import g

    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)
    g.end_exp()
    try:
        delete_kafka_topic(extra_vars)
    except:
        ...
        traceback.print_exc()
    for job_name in [
        "create-kafka-topic",
        "throughput",
        "delete-kafka-topic",
        "kafka-producer-perf-test",
    ]:
        try:
            job = Job(Box(metadata=Box(name=job_name, namespace="default")))
            job.delete(propagation_policy="Foreground")
            kubectl(split(f"delete job {job_name} -n default"))
        except:
            ...
            # traceback.print_exc()
            # breakpoint()
    scale_prometheus(0)


# if __name__ == "__main__":
#     exp("cluster=local uuid=1234")
