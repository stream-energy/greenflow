from pydantic import BaseModel
import pendulum

from pendulum import DateTime


class PlatformMetadata(BaseModel):
    pass


class G5KMetadata(PlatformMetadata):
    pass


class Metadata(BaseModel):
    deployment_ts: DateTime
    platform_metadata: PlatformMetadata
    # TODO: Add deployment ts and g5k metadata like job id


class Input(BaseModel):
    # TODO: Add g5k checks stuff, number of workers, etc
    pass


class Output(BaseModel):
    # TODO: Auto generated dashboards for that experiment run?
    pass


class Experiment(BaseModel):
    input: Input
    metadata: Metadata
    output: Output
