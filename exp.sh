#!/bin/bash

# Start with a load of 100,000
load=100000

# Run experiments with increasing load values
for _ in {1..4}; do
	echo "Running experiment with load ${load}"
	inv exp ingest-redpanda -l "${load}"
	load=$((load + 100000))
done
