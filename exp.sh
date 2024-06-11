#!/bin/bash

# yell() { echo "$0: $*" >&2; }
# die() { yell "$*"; exit 111; }
# try() { "$@" || die "cannot $*"; }

# inv setup ingest-redpanda

# inv redpanda
# inv kafka

# Enable debug and other shell options
set -euxo pipefail

# Start with a load of 500,000
load=10000
inv kafka
# Dummy experiment to warm up the cluster
inv exp ingest-kafka -l "${load}"
sleep 60

# Trap SIGINT and SIGTERM

# inv redpanda
# kubectl scale statefulset -n redpanda redpanda --replicas 3
# # Scale down kafka as we are running redpanda first
# kubectl scale deployment theodolite-kafka --replicas=0 || true

# Run experiments with increasing load values
# for _ in {1..25}; do
# 	echo "Running experiment with load ${load}"
# 	inv exp ingest-redpanda -l "${load}"
# 	inv exp ingest-kafka -l "${load}"
# 	load=$((load + 5000))
# done

# helm uninstall -n redpanda redpanda

# Deploy kafka
# inv kafka

# load=200000

# for _ in {1..10}; do
# 	echo "Running experiment with load ${load}"
# 	inv exp ingest-kafka -l "${load}"
# 	load=$((load + 200000))
# done

# kubectl delete kafka theodolite-kafka
# sleep 15
# Clean up Kafka
# kubectl scale deployments/strimzi-cluster-operator --replicas 0
# kubectl delete strimzipodsets theodolite-kafka-zookeeper
# kubectl delete strimzipodsets theodolite-kafka-kafka
# kubectl delete pvc data-theodolite-kafka-kafka-0 || true
# kubectl delete pvc data-theodolite-kafka-kafka-1 || true
# kubectl delete pvc data-theodolite-kafka-kafka-2 || true
