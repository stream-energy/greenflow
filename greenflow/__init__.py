from os import environ


def monkey_patch_g(deployment_type="production"):
    from .g import _g  # Adjust the import to your module's actual name
    import greenflow.g as g

    class Patched_g(_g):
        def __init__(self, deployment_type=deployment_type):
            if deployment_type == "test":
                import os
                os.environ["EXPERIMENT_STORAGE_URL"] = os.environ["TEST_EXPERIMENT_STORAGE_URL"]
                os.environ["PROMETHEUS_URL"] = os.environ["TEST_PROMETHEUS_URL"]
                os.environ["EXPERIMENT_PUSHGATEWAY_URL"] = os.environ[
                    "TEST_EXPERIMENT_PUSHGATEWAY_URL"
                ]
                os.environ["EXPERIMENT_BASE_URL"] = os.environ["TEST_EXPERIMENT_BASE_URL"]
            super().__init__(deployment_type)

    # Replace the original _g class with the patched one
    g._g = Patched_g

    # Optionally, replace the existing instance if needed
    g.g = Patched_g(deployment_type)
    import sys

    current_module = sys.modules[__name__]
    # setattr(current_module, "g", g)
    current_module.g = g
