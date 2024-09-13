import logging
from box import Box
from kr8s.objects import Job
import pendulum
import time

from entrypoint import rebind_parameters
from .exp_ng import create_kafka_topic, delete_kafka_topic
from .prometheus import reinit_prometheus, scale_prometheus

from ..g import g
from ..state import get_deployment_state_vars, get_experiment_state_vars
from ..factors import factors
from .synchronized_perf_script import synchronized_perf_script
from ..analysis import get_observed_throughput_of_last_experiment


def exp_hammer_job(extra_vars) -> Job:
    #TODO: Merge this with normal job
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
cat << 'EOF' > /tmp/synchronized_kafka_perf_test.sh
{synchronized_perf_script}
EOF
chmod +x /tmp/synchronized_kafka_perf_test.sh
/tmp/synchronized_kafka_perf_test.sh \
    --topic input \
    --num-records {int(total_messages)} \
    --record-size {exp_params['messageSize']} \
    --throughput -1 \
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
    job.create()

    # Assume that it can take up to 20 seconds to start the job
    gracePeriod = 20
    totalDuration = extra_vars["exp_params"]["durationSeconds"] + gracePeriod

    try:
        job.wait(["condition=Complete", "condition=Failed"], timeout=totalDuration * 10)
        if job.status.conditions[0].type == "Complete":
            job.delete(propagation_policy="Foreground")
            return
    except TimeoutError:
        breakpoint()
        # job.delete(propagation_policy="Foreground")
        return
    except KeyboardInterrupt:
        job.delete(propagation_policy="Foreground")
        return


def hammer() -> float:
    from pprint import pprint

    experiment_description = "Hammer"

    now = pendulum.now()
    g.init_exp(experiment_description)
    extra_vars = get_deployment_state_vars() | get_experiment_state_vars() | factors()
    extra_vars = Box(extra_vars)
    logging.warning(
        dict(
            msg="Hammering",
            messageSize=extra_vars.exp_params.messageSize,
            load=extra_vars.exp_params.load,
        )
    )

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
    return last_throughput
