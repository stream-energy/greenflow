import persistent
import pendulum


class Deployment(persistent.Persistent):
    def __init__(self, metadata):
        match metadata:
            case {
                "type": "g5k",
            }:
                self.metadata = metadata
                self.started_ts = metadata["job_started_ts"]
            case {"type": "mock"}:
                self.metadata = metadata
                self.started_ts = pendulum.now().to_iso8601_string()
            case _:
                raise NotImplementedError

    def to_dict(self) -> dict:
        return dict(
            {
                "metadata": self.metadata,
                "started_ts": self.started_ts.format("YYYY-MM-DDTHH:mm:ssZ"),
            }
        )
