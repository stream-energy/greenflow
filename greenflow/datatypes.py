from pydantic import BaseModel
import pendulum

from pendulum import DateTime

# FIXME: Rethink whether we want pydantic validation for inputs and outputs
# Probably not for this iteration.


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
