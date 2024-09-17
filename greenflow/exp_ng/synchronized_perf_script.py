synchronized_perf_script = """
#!/bin/bash

# Echo out the command line arguments
echo "$@"

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
            --throughput)
                THROUGHPUT="$2"
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
            --durationSeconds)
                DURATION_SECONDS="$2"
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

# Add 5 seconds to the duration to allow for graceful termination
DURATION_SECONDS=$((DURATION_SECONDS + 5))

# Validate required parameters
if [[ -z "$TOPIC" || -z "$NUM_RECORDS" || -z "$RECORD_SIZE" || -z "$PRODUCER_PROPS" || -z "$START_TIMESTAMP" || -z "$DURATION_SECONDS" ]]; then
    echo "Missing required parameters. Usage:"
    echo "./synchronized_kafka_perf_test.sh --topic <topic> --num-records <num> --record-size <size> --producer-props <props> --start-timestamp <unix_timestamp> --durationSeconds <seconds>"
    exit 1
fi

# Wait until the specified start time
CURRENT_TIME=$(date +%s)
if [ "$START_TIMESTAMP" -gt "$CURRENT_TIME" ]; then
    SLEEP_DURATION=$((START_TIMESTAMP - CURRENT_TIME))
    echo "Waiting for $SLEEP_DURATION seconds before starting the test..."
    echo "Waiting until $(date -d @$START_TIMESTAMP)"
    sleep $SLEEP_DURATION
else
    echo "Warning: Start time is in the past. Starting immediately."
fi

# Log the actual start time
ACTUAL_START_TIME=$(date +%s)
echo "Test started at: $(date -d @$ACTUAL_START_TIME)"

# Run the Kafka producer performance test in the background
kafka-producer-perf-test \
    --topic "$TOPIC" \
    --num-records "$NUM_RECORDS" \
    --record-size "$RECORD_SIZE" \
    --throughput "$THROUGHPUT" \
    --producer-props "$PRODUCER_PROPS" \
    --print-metrics &

PERF_TEST_PID=$!

# Set up the time bomb
(
    echo "Will kill the performance test in $DURATION_SECONDS seconds at $(date -d @$((ACTUAL_START_TIME + DURATION_SECONDS)))"
    sleep "$DURATION_SECONDS"
    echo "Time's up! Killing the performance test."
    kill -TERM $PERF_TEST_PID
    sleep 5
    if kill -0 $PERF_TEST_PID 2>/dev/null; then
        echo "Performance test didn't terminate gracefully. Forcing kill."
        kill -KILL $PERF_TEST_PID
    fi
) &
TIMEBOMB_PID=$!

# Wait for the performance test to finish or be killed
wait $PERF_TEST_PID
TEST_EXIT_STATUS=$?

# Kill the time bomb if the test finishes before the time is up
kill $TIMEBOMB_PID 2>/dev/null

# Log the end time
END_TIME=$(date +%s)
echo "Test ended at: $END_TIME"

# Calculate and print the total duration
ACTUAL_DURATION=$((END_TIME - ACTUAL_START_TIME))
echo "Total test duration: $ACTUAL_DURATION seconds"

# Exit with the status of the performance test
exit 0
"""
