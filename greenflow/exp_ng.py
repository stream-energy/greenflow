import threading
import traceback
from kr8s.objects import Job
import time
from sh import kubectl
from shlex import split

from box import Box, BoxList

from .factors import factors
from .playbook import _playbook
from .state import get_deployment_state_vars, get_experiment_state_vars


def create_job(extra_vars) -> Job:
    pushgateway_url = extra_vars["prometheus_pushgateway_url"]
    exp_params = extra_vars["exp_params"]
    args = BoxList(
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
                "ttlSecondsAfterFinished": 100,
                "backoffLimit": 0,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "create-topic",
                                "image": "registry.gitlab.inria.fr/gkovilkk/greenflow/redpanda:v24.1.8",
                                "command": ["rpk"],
                                "args": args,
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
                "ttlSecondsAfterFinished": 15,
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
                "ttlSecondsAfterFinished": 15,
                "template": {
                    "metadata": {"labels": {"app": "kafka-producer-perf-test"}},
                    "spec": {
                        "restartPolicy": "Never",
                        "terminationGracePeriodSeconds": 0,
                        "nodeSelector": {"node.kubernetes.io/worker": "true"},
                        "containers": [
                            {
                                "name": "kafka-producer-perf-test",
                                "image": "confluentinc/cp-kafka:latest",
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
                "ttlSecondsAfterFinished": 15,
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
        return
    else:
        raise RuntimeError("Failed to create kafka topic")


def deploy_experiment(extra_vars) -> Job:
    job = exp_job(extra_vars)
    # job = exp_job_custom(extra_vars)
    job.create()

    gracePeriod = 30
    totalDuration = extra_vars["exp_params"]["durationSeconds"] + gracePeriod

    try:
        job.wait(["condition=Complete", "condition=Failed"], timeout=totalDuration)
    except TimeoutError:
        job.delete(propagation_policy="Foreground")
        return


def delete_kafka_topic(extra_vars):
    job = delete_job(extra_vars)
    job.create()
    job.wait(["condition=Complete", "condition=Failed"])
    if job.status.conditions[0].type == "Complete":
        return
    else:
        raise RuntimeError("Failed to delete kafka topic")


def exp_ng(exp_name, experiment_description):
    from .playbook import _playbook
    from .g import g

    g.init_exp(exp_name, experiment_description)
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)

    create_kafka_topic(extra_vars)
    deploy_experiment(extra_vars)

    # Chill for a bit
    time.sleep(30)

    delete_kafka_topic(extra_vars)

    g.end_exp()


def killexp():
    from .g import g
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)
    g.end_exp()
    try:
        delete_kafka_topic(extra_vars)
    except:
        ...
        traceback.print_exc()
        breakpoint()
    for job_name in ["create-kafka-topic", "throughput", "delete-kafka-topic"]:
        try:
            job = Job(Box(metadata=Box(name=job_name, namespace="default")))
            job.delete(propagation_policy="Foreground")
            kubectl(split(f"delete job {job_name} -n default"))
        except:
            ...
            # traceback.print_exc()
            # breakpoint()


if __name__ == "__main__":
    exp_ng("ingest-kafka", "cluster=local uuid=1234")
