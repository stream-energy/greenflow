import os
import pytest
import pendulum
import transaction
from unittest.mock import Mock, patch
from entrypoint import load_gin
from greenflow.g import _g
from greenflow.experiment import Experiment

@pytest.fixture
def mock_env(tmp_path):
    """Setup test environment variables"""
    os.environ["TEST_EXPERIMENT_STORAGE_URL"] = "mock://test"
    os.environ["TEST_PROMETHEUS_URL"] = "mock://test"
    os.environ["TEST_EXPERIMENT_PUSHGATEWAY_URL"] = "mock://test"
    os.environ["TEST_DASHBOARD_BASE_URL"] = "mock://test"
    yield tmp_path

@pytest.fixture
def g(mock_env):
    """Initialize test g instance"""
    return load_gin("ingest-redpanda", test=True)

def test_experiment_lifecycle(g):
    """Test the complete experiment lifecycle"""
    # Initialize experiment
    g.init_exp("Test experiment")
    assert g.root.current_experiment is not None
    assert g.root.current_experiment.exp_name == "ingest-redpanda"  # from factors
    assert g.root.current_experiment.experiment_description == "Test experiment"
    
    # Verify timestamps
    start_ts = pendulum.parse(g.root.current_experiment.started_ts)
    assert (pendulum.now() - start_ts).in_seconds() < 1
    
    g.end_exp()
    
    # Verify experiment data
    exp_dict = g.root.current_experiment.to_dict()
    assert exp_dict["exp_name"] == "ingest-redpanda"
    assert exp_dict["experiment_description"] == "Test experiment"
    assert "started_ts" in exp_dict
    assert "stopped_ts" in exp_dict
    assert float(exp_dict["experiment_metadata"]["results"]["duration"]) > 0

def test_experiment_results_calculation(g):
    """Test experiment results calculation"""
    g.init_exp("Test experiment")
    
    # Mock time passage
    start = pendulum.now()
    with patch('pendulum.now') as mock_now:
        mock_now.return_value = start.add(seconds=10)
        g.end_exp()
    
    results = g.root.current_experiment.results
    assert abs(results["duration"] - 10.0) < 0.1

def test_storage_persistence(g, mock_env):
    """Test that experiments are properly stored in MongoDB"""
    # Create and end experiment
    g.init_exp("Test persistence")
    g.end_exp()
    
    # Get experiment from storage
    stored_exp = g.storage.find_experiments_by_timerange(
        g.root.current_experiment.started_ts,
        g.root.current_experiment.started_ts,
    )[0]
    
    # Verify stored data matches
    assert stored_exp.exp_name == "ingest-redpanda"
    assert stored_exp.experiment_description == "Test persistence"
    assert stored_exp.started_ts is not None
    assert stored_exp.stopped_ts is not None
    assert stored_exp.experiment_metadata is not None
    
    # Clean up
    g.storage.delete_experiment(stored_exp._id)
