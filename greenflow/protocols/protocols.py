from pdb import post_mortem
import time
from box import Box
from greenflow.exp_ng.hammer import hammer, stress_test
from greenflow.exp_ng.exp_ng import killexp
from entrypoint import (
    rebind_parameters,
    load_gin,
    send_notification,
    kafka_context,
    redpanda_context,
)
import traceback
import logging

from greenflow.exp_ng.prometheus import reinit_prometheus
from ..state import get_deployment_state_vars, get_experiment_state_vars
from ..factors import factors


def safety_curve(exp_description) -> None:
    from greenflow.playbook import exp
    from greenflow.adaptive import threshold_hammer

    exp_name = "ingest-kafka"
    load_gin("ingest-kafka")

    # Message sizes up to 1MB (with
    messageSizes = [2**i for i in range(5, 17)] + [1048376]

    for _ in range(3):
        try:
            exp_name = "ingest-kafka"
            load_gin(exp_name)
            with kafka_context():
                threshold_hammer(exp_description, messageSizes)
            exp_name = "ingest-redpanda"
            load_gin(exp_name)
            with redpanda_context():
                threshold_hammer(exp_description, messageSizes)
        except:
            send_notification("Error in experiment. Debugging with shell")
            traceback.print_exc()
            post_mortem()

    send_notification("Experiment complete. On to the next.")


def run_single_hammer(exp_name, *, exp_description, **params):
    ctx_manager = kafka_context if exp_name == "ingest-kafka" else redpanda_context
    params = Box(params)

    try:
        rebind_parameters(**params)
        with ctx_manager():
            return hammer(exp_description)
    except Exception as e:
        traceback.print_exc()
        send_notification(
            f"Error in {exp_name} experiment with: {str(e)}",
            priority="max",
        )
        traceback.print_exc()
        post_mortem()
        try:
            killexp()  # Clean up
        except Exception as cleanup_error:
            logging.error(f"Error during cleanup: {str(cleanup_error)}")


def scaling_behaviour(exp_description) -> None:
    brokerReplicaList = list(range(1, 11))
    exp_name = "ingest-kafka"
    load_gin(exp_name)
    rebind_parameters(consumerInstances=10, producerInstances=10, partitions=120)

    for _ in range(3):
        for replicas in brokerReplicaList:
            run_single_hammer(
                exp_name,
                exp_description=exp_description,
                brokerReplicas=replicas,
                partitions=replicas * 10,
            )

    exp_name = "ingest-redpanda"
    load_gin(exp_name)
    rebind_parameters(consumerInstances=10, producerInstances=10, partitions=120)
    for _ in range(3):
        for replicas in brokerReplicaList:
            run_single_hammer(
                exp_name,
                exp_description=exp_description,
                brokerReplicas=replicas,
                partitions=replicas * 10,
            )

    send_notification("Experiment complete. On to the next.")


def proportionality(exp_description) -> None:
    # for exp_name in ["ingest-kafka", "ingest-redpanda"]:
    #     ctx_manager = kafka_context if exp_name == "ingest-kafka" else redpanda_context
    #     load_gin(exp_name)
    #     with ctx_manager():
    #         rebind_parameters(durationSeconds=300)
    #         baseline = stress_test(
    #             target_load=100, exp_description=exp_description
    #         )
    for exp_name in ["ingest-kafka", "ingest-redpanda"]:
        ctx_manager = kafka_context if exp_name == "ingest-kafka" else redpanda_context
        load_gin(exp_name)
        with ctx_manager():
            from ..g import g

            rebind_parameters(durationSeconds=300, load=0)
            g.init_exp(exp_description)
            extra_vars = (
                get_deployment_state_vars() | get_experiment_state_vars() | factors()
            )
            extra_vars = Box(extra_vars)
            reinit_prometheus(
                extra_vars["deployment_started_ts"], extra_vars["experiment_started_ts"]
            )
            time.sleep(300)
            g.end_exp()
            # rebind_parameters(durationSeconds=300)
            # baseline = stress_test(
            #     target_load=100, exp_description=exp_description
            # )
    # for exp_name in ["ingest-kafka", "ingest-redpanda"]:
    #     load_gin(exp_name)
    #     ctx_manager = kafka_context if exp_name == "ingest-kafka" else redpanda_context

    #     with ctx_manager():
    #         baseline = stress_test(
    #             target_load=1 * 10**9, exp_description=exp_description
    #         )
    #         # Then test at 10% intervals
    #         for percentage in range(10, 101, 10):
    #             load_factor = percentage / 100.0
    #             stress_test(
    #                 target_load=baseline * load_factor, exp_description=exp_description
    #             )

    for exp_name in ["ingest-kafka", "ingest-redpanda"]:
        load_gin(exp_name)
        rebind_parameters(partitions=300, consumerInstances=10, producerInstances=10)
        ctx_manager = kafka_context if exp_name == "ingest-kafka" else redpanda_context

        with ctx_manager():
            baseline = stress_test(
                target_load=1 * 10**9, exp_description=exp_description
            )
            # Then test at 10% intervals
            for percentage in range(10, 101, 10):
                load_factor = percentage / 100.0
                stress_test(
                    target_load=baseline * load_factor, exp_description=exp_description
                )

    send_notification("Proportionality experiments complete.")
