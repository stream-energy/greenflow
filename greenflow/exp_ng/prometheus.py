from kr8s.objects import new_class

# Define the Prometheus custom resource
Prometheus = new_class(
    plural="prometheuses",
    kind="Prometheus",
    version="monitoring.coreos.com/v1",
    namespaced=True,
    scalable=True,
    scalable_spec="replicas",  # The spec key to patch when scaling
)


def reinit_prometheus(deployment_started_ts, experiment_started_ts):
    # Create a CustomResource object for the Prometheus CRD
    prometheus = Prometheus.get(
        "kp-kube-prometheus-stack-prometheus", namespace="default"
    )

    # Prepare the patch data
    patch_data = {
        "spec": {
            "replicas": 1,
            "externalLabels": {
                "deployment_started_ts": deployment_started_ts,
                "experiment_started_ts": experiment_started_ts,
            },
        }
    }

    # Apply the patch
    prometheus.patch(patch_data)
    prometheus.wait(
        ["condition=Available", "condition=Reconciled"], mode="all", timeout=120
    )


def scale_prometheus(replicas):
    # Create a CustomResource object for the Prometheus CRD
    prometheus = Prometheus.get(
        "kp-kube-prometheus-stack-prometheus", namespace="default"
    )
    prometheus.scale(replicas)
    prometheus.wait(
        ["condition=Available", "condition=Reconciled"], mode="all", timeout=60
    )
