import pendulum
import persistent


class Experiment(persistent.Persistent):
    def __init__(self):
        from .factors import factors
        from .g import g

        self.factors = factors()
        self.deployment_metadata = g.root.current_deployment.metadata
        self.started_ts = pendulum.now()

    def to_dict(self) -> dict:
        from .utils import generate_explore_url, generate_grafana_dashboard_url

        return dict(
            {
                "factors": self.factors,
                "deployment_metadata": self.deployment_metadata,
                "started_ts": self.started_ts.format("YYYY-MM-DDTHH:mm:ssZ"),
                "stopped_ts": self.stopped_ts.format("YYYY-MM-DDTHH:mm:ssZ"),
                "dashboard_url": generate_grafana_dashboard_url(
                    started_ts=self.started_ts, stopped_ts=self.stopped_ts
                ),
                "explore_url": generate_explore_url(
                    started_ts=self.started_ts, stopped_ts=self.stopped_ts
                ),
            }
        )
