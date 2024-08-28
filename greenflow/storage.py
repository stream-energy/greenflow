class ExpStorage:
    from .g import g

    def __init__(self, path=f"{g.gitroot}/storage/experiment-history.yaml") -> None:
        from tinydb import TinyDB
        from tinydb_serialization import SerializationMiddleware

        from .utils import DateTimeSerializer, YAMLStorage

        serialization = SerializationMiddleware(YAMLStorage)
        serialization.register_serializer(DateTimeSerializer(), "Pendulum")
        self.experiments = TinyDB(
            path,
            storage=serialization,
        )

    def commit_experiment(self) -> None:
        from .g import g

        self.experiments.insert(g.root.current_experiment.to_dict())
