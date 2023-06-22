class ExpStorage:
    def __init__(self) -> None:
        from tinydb import TinyDB
        from tinydb_serialization import SerializationMiddleware

        from .utils import DateTimeSerializer, YAMLStorage

        serialization = SerializationMiddleware(YAMLStorage)
        serialization.register_serializer(DateTimeSerializer(), "Pendulum")
        self.experiments = TinyDB(
            "storage/experiment-history.yaml",
            storage=serialization,
        )

    def create_new_experiment(self):
        from .g import g

        g.init_exp()

    def commit_experiment(self) -> None:
        from .g import g

        self.experiments.insert(g.root.current_experiment.to_dict())
