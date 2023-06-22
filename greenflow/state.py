#!/usr/bin/env python3
def get_deployment_state_vars():
    from .g import g

    return {
        "deployment_started_ts": (
            g.root.current_deployment.started_ts.format("YYYY-MM-DDTHH:mm:ssZ")
        ),
        "kubeconfig_path": "../../kubeconfig",
        "gitroot": g.gitroot,
    }


def get_experiment_state_vars():
    from .g import g

    return {
        "experiment_started_ts": (
            g.root.current_experiment.started_ts.format("YYYY-MM-DDTHH:mm:ssZ")
        ),
    }
