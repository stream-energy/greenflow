import logging
import traceback


def memory_cpu_impact_10_10_120(exp_description):
    from greenflow.exp_ng.hammer import hammer
    from greenflow.exp_ng.exp_ng import killexp
    from greenflow.playbook import exp
    from greenflow.adaptive import threshold_hammer
    from entrypoint import (
        rebind_parameters,
        load_gin,
        send_notification,
        kafka_context,
        redpanda_context,
    )

    exp_name = "ingest-kafka"
    mems = ["1Gi", "2Gi", "4Gi", "8Gi", "16Gi"]
    cpus = [1, 2, 4, 6, 8]
    load_gin(exp_name)
    rebind_parameters(
        consumerInstances=10, producerInstances=10, partitions=120, brokerReplicas=3
    )

    for _ in range(3):
        for mem in mems:
            for cpu in cpus:
                try:
                    rebind_parameters(brokerMem=mem, brokerCpu=cpu)
                    with kafka_context():
                        hammer(exp_description)
                except Exception as e:
                    logging.error(
                        f"Error in Kafka experiment with mem={mem}, cpu={cpu}: {str(e)}"
                    )
                    traceback.print_exc()
                    send_notification(
                        f"Error in Kafka experiment with mem={mem}, cpu={cpu}: {str(e)}"
                    )
                    try:
                        killexp()  # Clean up
                    except Exception as cleanup_error:
                        logging.error(f"Error during cleanup: {str(cleanup_error)}")
                    continue  # Move to next iteration

    # Redpanda experiments
    exp_name = "ingest-redpanda"
    load_gin(exp_name)
    rebind_parameters(
        consumerInstances=10, producerInstances=10, partitions=120, brokerReplicas=3
    )

    # Helper function to convert memory string to GiB number
    def mem_to_gib(mem_str):
        return int(mem_str.replace("Gi", ""))

    for _ in range(3):
        for mem in mems:
            mem_gib = mem_to_gib(mem)
            for cpu in cpus:
                # Skip if memory per core is less than 1GiB
                if mem_gib / cpu < 1:
                    logging.info(
                        f"Skipping configuration mem={mem}, cpu={cpu} due to insufficient memory per core"
                    )
                    continue

                try:
                    rebind_parameters(brokerMem=mem, brokerCpu=cpu)
                    with redpanda_context():
                        hammer(exp_description)
                except Exception as e:
                    logging.error(
                        f"Error in Redpanda experiment with mem={mem}, cpu={cpu}: {str(e)}"
                    )
                    traceback.print_exc()
                    try:
                        killexp()  # Clean up
                    except Exception as cleanup_error:
                        logging.error(f"Error during cleanup: {str(cleanup_error)}")
                    continue  # Move to next iteration

    send_notification("Experiment complete. On to the next.")


def memory_cpu_impact_1_1_1(exp_description):
    from greenflow.exp_ng.hammer import hammer
    from greenflow.exp_ng.exp_ng import killexp
    from greenflow.playbook import exp
    from greenflow.adaptive import threshold_hammer
    from entrypoint import (
        rebind_parameters,
        load_gin,
        send_notification,
        kafka_context,
        redpanda_context,
    )

    # # Kafka experiments
    exp_name = "ingest-kafka"
    mems = ["1Gi", "2Gi", "4Gi", "8Gi", "16Gi"]
    cpus = [1, 2, 4, 6, 8]
    load_gin(exp_name)
    rebind_parameters(
        consumerInstances=1, producerInstances=1, partitions=1, brokerReplicas=1
    )

    for _ in range(3):
        for mem in mems:
            for cpu in cpus:
                try:
                    rebind_parameters(brokerMem=mem, brokerCpu=cpu)
                    with kafka_context():
                        hammer(exp_description)
                except Exception as e:
                    logging.error(
                        f"Error in Kafka experiment with mem={mem}, cpu={cpu}: {str(e)}"
                    )
                    traceback.print_exc()
                    send_notification(
                        f"Error in Kafka experiment with mem={mem}, cpu={cpu}: {str(e)}"
                    )
                    try:
                        killexp()  # Clean up
                    except Exception as cleanup_error:
                        logging.error(f"Error during cleanup: {str(cleanup_error)}")
                    continue  # Move to next iteration

    # Redpanda experiments
    exp_name = "ingest-redpanda"
    load_gin(exp_name)
    rebind_parameters(
        consumerInstances=1, producerInstances=1, partitions=1, brokerReplicas=1
    )

    # Helper function to convert memory string to GiB number
    def mem_to_gib(mem_str):
        return int(mem_str.replace("Gi", ""))

    for _ in range(3):
        for mem in mems:
            mem_gib = mem_to_gib(mem)
            for cpu in cpus:
                # Skip if memory per core is less than 1GiB
                if mem_gib / cpu < 1:
                    logging.info(
                        f"Skipping configuration mem={mem}, cpu={cpu} due to insufficient memory per core"
                    )
                    continue

                try:
                    rebind_parameters(brokerMem=mem, brokerCpu=cpu)
                    with redpanda_context():
                        hammer(exp_description)
                except Exception as e:
                    logging.error(
                        f"Error in Redpanda experiment with mem={mem}, cpu={cpu}: {str(e)}"
                    )
                    traceback.print_exc()
                    try:
                        killexp()  # Clean up
                    except Exception as cleanup_error:
                        logging.error(f"Error during cleanup: {str(cleanup_error)}")
                    continue  # Move to next iteration

    send_notification("Experiment complete. On to the next.")
