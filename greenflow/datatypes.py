import pendulum
import persistent
from pendulum import DateTime
from pydantic import BaseModel


class Deployment(persistent.Persistent):
    def __init__(self, metadata):
        match metadata:
            case {
                "type": "g5k",
            }:
                self.metadata = metadata
                self.started_ts = metadata["job_started_ts"]
            case _:
                raise NotImplementedError


class PlatformMetadata(BaseModel):
    pass


class G5KMetadata(PlatformMetadata):
    pass


class Metadata(BaseModel):
    deployment_ts: DateTime
    platform_metadata: PlatformMetadata


class Input(BaseModel):
    pass


class Output(BaseModel):
    pass


class Experiment(BaseModel):
    input: Input
    metadata: Metadata
    output: Output
