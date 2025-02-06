from typing import Any as Any, Generator
import pytest
from os import environ
from pytest_docker_tools import container
from greenflow.mongo_storage import ExpStorage, Experiment
from os import getenv
import pendulum
from copy import deepcopy

# MongoDB container for testing
# mongodb = container(
#     name="test-mongodb",
#     image="mongo:7.0",
#     ports={27017: 27018},
#     scope="session",
# )


@pytest.fixture()
def storage() -> Generator[ExpStorage, Any, None]:
    """Fixture for ExpStorage instance"""
    storage = ExpStorage(
        url=f"mongodb://root:{getenv('MONGO_PASSWORD')}@localhost:27017/",
        db_name="test_exp_db",
    )

    yield storage

    storage.client.drop_database("test_exp_db")


class TestExperiment:
    def test_create_experiment(self, storage):
        exp = Experiment(exp_name="test_exp", experiment_description="Test description")

        assert exp.exp_name == "test_exp"
        assert exp.experiment_description == "Test description"
        assert isinstance(exp.started_ts, str)
        assert isinstance(exp.stopped_ts, str)

    def test_calculate_results(self, storage):
        exp = Experiment(exp_name="test_duration")
        start_time = pendulum.now()
        exp.started_ts = start_time.to_iso8601_string()
        exp.stopped_ts = start_time.add(seconds=10).to_iso8601_string()

        exp.calculate_results()

        assert "duration" in exp.results
        assert exp.results["duration"] >= 10.0


class TestExpStorage:
    def test_find_experiments_by_name(self, storage):
        exp1 = Experiment(exp_name="test1")
        exp2 = Experiment(exp_name="test2")

        storage.save_experiment(exp1)
        storage.save_experiment(exp2)

        results = storage.find_experiments_by_name("test1")
        assert len(results) == 1
        assert all(exp.exp_name == "test1" for exp in results)

    def test_find_experiments_by_timerange(self, storage):
        now = pendulum.now()

        exp1 = Experiment(
            exp_name="past", started_ts=now.subtract(hours=2).to_iso8601_string()
        )
        exp2 = Experiment(exp_name="present", started_ts=now.to_iso8601_string())
        exp3 = Experiment(
            exp_name="future", started_ts=now.add(hours=2).to_iso8601_string()
        )

        for exp in [exp1, exp2, exp3]:
            storage.save_experiment(exp)

        results = storage.find_experiments_by_timerange(
            start=now.subtract(hours=3), end=now.add(hours=1)
        )

        assert len(results) == 2
        assert any(exp.exp_name == "past" for exp in results)
        assert any(exp.exp_name == "present" for exp in results)

    def test_find_experiments_by_params(
        self, storage: ExpStorage, sample_experiment_data
    ):
        """Test finding experiments with specific parameters"""
        exp1 = Experiment.from_dict(sample_experiment_data)

        # Create another experiment with different params
        modified_data = deepcopy(sample_experiment_data)
        modified_data["experiment_metadata"]["factors"]["exp_params"].update(
            {"broker_cpu": 20, "load": 60000}
        )
        exp2 = Experiment.from_dict(modified_data)

        storage.save_experiment(exp1)
        storage.save_experiment(exp2)

        # Find experiments with specific params
        results = storage.find_experiments_by_params({"broker_cpu": 10})

        assert len(results) == 1
        assert results[0].factors["exp_params"]["broker_cpu"] == 10
        assert results[0].factors["exp_params"]["load"] == 50000

    @pytest.mark.parametrize(
        "params,expected_count",
        [
            ({"broker_replicas": 3, "load": 50000}, 1),
            ({"broker_replicas": 5, "load": 50000}, 0),
            ({"consumer_instances": 10, "producer_instances": 10}, 1),
            ({"messageSize": 256}, 0),
        ],
    )
    def test_parameterized_param_search(
        self, storage, sample_experiment_data, params, expected_count
    ):
        """Test finding experiments with different parameter combinations"""
        exp = Experiment(**sample_experiment_data)
        storage.save_experiment(exp)

        results = storage.find_experiments_by_params(params)
        assert len(results) == expected_count


@pytest.fixture
def sample_experiment_data() -> dict[str, any]:
    return {
        "exp_name": "ingest-kafka",
        "experiment_description": "cluster=taurus bw=10G memImpact=true",
        "started_ts": "2025-01-10T12:49:43.111220+01:00",
        "stopped_ts": "2025-01-10T12:52:15.561292+01:00",
        "experiment_metadata": {
            "factors": {
                "exp_name": "ingest-kafka",
                "exp_params": {
                    "broker_cpu": 10,
                    "broker_io_threads": 10,
                    "broker_mem": "4Gi",
                    "broker_network_threads": 10,
                    "broker_replicas": 3,
                    "consumer_instances": 10,
                    "durationSeconds": 100,
                    "kafka_bootstrap_servers": "theodolite-kafka-kafka-bootstrap:9092",
                    "load": 50000,
                    "messageSize": 128,
                    "partitions": 100,
                    "producer_instances": 10,
                    "redpanda_write_caching": True,
                    "replicationFactor": 1,
                    "warmupSeconds": 0,
                },
            },
            "deployment_metadata": {
                "ansible_inventory": {
                    "all": {
                        "children": {
                            "broker": {
                                "hosts": {
                                    "taurus-11.lyon.grid5000.fr": {
                                        "kubernetes_role": "broker"
                                    },
                                    "taurus-13.lyon.grid5000.fr": {
                                        "kubernetes_role": "broker"
                                    },
                                }
                            },
                            "control": {
                                "hosts": {
                                    "taurus-1.lyon.grid5000.fr": {
                                        "kubernetes_role": "control_plane"
                                    }
                                }
                            },
                        }
                    }
                },
                "job_id": 1783162,
                "job_site": "lyon",
                "job_started_ts": "2025-01-10T00:57:06+01:00",
                "type": "g5k",
            },
            "results": {"duration": 152.450072},
        },
    }


class TestExperimentRealistic:
    def test_experiment_serialization(self, storage, sample_experiment_data):
        """Test that experiment serializes correctly to MongoDB format"""
        exp = Experiment.from_dict(sample_experiment_data)
        doc = exp.to_doc()

        assert doc["exp_name"] == sample_experiment_data["exp_name"]
        assert doc["experiment_metadata"]["factors"]["exp_params"]["broker_cpu"] == 10
        assert "dashboard_url" in doc["experiment_metadata"]
