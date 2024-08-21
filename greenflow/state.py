#!/usr/bin/env python3
import os


def get_deployment_state_vars():
    from .g import g
    try:
        return {
            "deployment_started_ts": (
                g.root.current_deployment.started_ts.format("YYYY-MM-DDTHH:mm:ssZ")
            ),
            "kubeconfig_path": "../../kubeconfig",
            "gitroot": g.gitroot,
            "deployment_type": g.deployment_type,
        }
    except AttributeError:
        return {
            "deployment_started_ts": "1970-01-01T00:00:00Z",
            "kubeconfig_path": "../../kubeconfig",
            "gitroot": g.gitroot,
            "deployment_type": "production",
        }


def get_experiment_state_vars():
    from .g import g

    return {
        "experiment_started_ts": (
            g.root.current_experiment.started_ts.format("YYYY-MM-DDTHH:mm:ssZ")
        ),
        "prometheus_pushgateway_url": os.getenv("EXPERIMENT_PUSHGATEWAY_URL"),
    }
