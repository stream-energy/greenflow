import json
from os import environ

import pendulum
import yaml
from pendulum.datetime import DateTime
from tinydb import Storage
from tinydb_serialization import Serializer


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def get_readable_gin_config() -> dict:
    """
    Parses the gin configuration to a dictionary. Useful for logging to e.g. W&B
    :param gin_config: the gin's config dictionary. Can be obtained by gin.config._OPERATIVE_CONFIG
    :return: the parsed (mainly: cleaned) dictionary
    """
    from gin.config import _OPERATIVE_CONFIG as gin_config

    data = {}
    for key in gin_config.keys():
        name = key[1]
        # name = key[1].split(".")[1]
        values = gin_config[key]

        if values:
            subdict = {}
            for k, v in values.items():
                if is_jsonable(v):
                    subdict[k] = v
                else:
                    subdict[k] = v.__str__()
            data[name] = subdict

    return data


class YAMLStorage(Storage):
    def __init__(self, filename):  # (1)
        self.filename = filename

    def read(self):
        try:
            with open(self.filename) as handle:
                try:
                    data = yaml.safe_load(handle.read())  # (2)
                    return data
                except yaml.YAMLError:
                    return None  # (3)
        except FileNotFoundError:
            return None

    def write(self, data):
        with open(self.filename, "w+") as handle:
            yaml.dump(data, handle)

    def close(self):  # (4)
        pass


class DateTimeSerializer(Serializer):
    OBJ_CLASS = DateTime

    def encode(self, obj: DateTime):
        return obj.to_iso8601_string()

    def decode(self, s):
        return pendulum.parse(s, strict=False)


def generate_explore_url(*, started_ts: DateTime, stopped_ts: DateTime) -> str:
    return f"{environ['EXPERIMENT_BASE_URL']}/explore?orgId=1&left=%7B%22datasource%22:%22IS5LGzoVk%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22datasource%22:%7B%22type%22:%22prometheus%22,%22uid%22:%22IS5LGzoVk%22%7D%7D%5D,%22range%22:%7B%22from%22:%22{int(started_ts.float_timestamp*1000)}%22,%22to%22:%22{int(stopped_ts.float_timestamp*1000)}%22%7D%7D"


def generate_grafana_dashboard_url(
    *,
    started_ts: DateTime,
    stopped_ts: DateTime,
    base_url: str = f"{environ['EXPERIMENT_BASE_URL']}/d/76thsXBVk/greenflow?",
) -> str:
    return f"{base_url}from={int(started_ts.float_timestamp*1000)}&to={int(stopped_ts.float_timestamp*1000)}"
