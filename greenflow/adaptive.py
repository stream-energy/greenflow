from typing import Callable, NamedTuple, Any
import pendulum
from abc import ABC, abstractmethod



class State(NamedTuple):
    params: dict[str, Any]
    time: pendulum.DateTime


class Result(NamedTuple):
    metrics: dict[str, Any]
    time: pendulum.DateTime


class History(NamedTuple):
    states: list[State]
    results: list[Result]


class Decision(NamedTuple):
    next_params: dict[str, Any]


class AdaptiveExperiment(ABC):
    def __init__(
        self,
        executor: Callable[[State], Result],
        initial_params: dict[str, Any],
        max_iter: int = 10,
    ):
        self.initial_params = initial_params
        self.max_iter = max_iter
        self.experiment = executor

    @abstractmethod
    def decide(self, history: History) -> Decision | None:
        pass

    def execute(self) -> History:
        history = History(states=[], results=[])

        def recurse(
            history: History, params: dict[str, Any], iteration: int
        ) -> History:
            if iteration >= self.max_iter:
                return history

            state = State(params=params, time=pendulum.now())
            result = self.experiment(state)

            new_history = History(
                states=history.states + [state], results=history.results + [result]
            )

            decision = self.decide(new_history)
            if decision is None:
                return new_history

            return recurse(new_history, decision.next_params, iteration + 1)

        return recurse(history, self.initial_params, 0)


class ThresholdLoadTest(AdaptiveExperiment):
    def __init__(
        self,
        *,
        executor: Callable[[State], Result],
        initial_params: dict[str, Any],
        max_iter: int = 10,
        exp_name: str,
        exp_description: str,
    ):
        super().__init__(executor, initial_params, max_iter)
        self.name = exp_name
        self.desc = exp_description

    def decide(self, history: History) -> Decision | None:
        if not history.states:
            return Decision(next_params=self.initial_params)

        current = history.states[-1].params
        result = history.results[-1].metrics
        load = current["load"]
        throughput = result["throughput"]

        threshold = 0.1
        diff = abs(load - throughput) / load

        low = current.get("low", 1 * 10**4)
        high = current.get("high", 1 * 10**6)

        if diff <= threshold:
            low = load
        elif throughput < load * (1 - threshold):
            high = load
        else:
            low = load

        if high - low < load * 0.05:
            return None  # Stop the experiment

        next_load = (low + high) // 2
        return Decision(
            next_params={**current, "load": next_load, "low": low, "high": high}
        )


def find_threshold_load(*, exp_name, message_size, description, previous_results=None):
    from greenflow.playbook import exp
    from entrypoint import rebind_parameters

    def experiment(state: State) -> Result:
        from greenflow.playbook import exp
        from greenflow.analysis import get_observed_throughput_of_last_experiment

        params = state.params

        load = params["load"]
        message_size = params["message_size"]
        start_time = pendulum.now()
        print(f"Starting with load {load} and message size {message_size}")
        rebind_parameters(load=load, message_size=message_size)
        exp(
            exp_name=params["exp_name"],
            experiment_description=params["exp_description"],
        )
        throughput = get_observed_throughput_of_last_experiment(
            minimum_current_ts=start_time
        )
        print(f"Done with load {load}. Observed throughput: {throughput}")
        return Result(metrics={"throughput": throughput}, time=state.time)

    # Adjust initial load based on previous results
    if previous_results:
        prev_message_size, prev_threshold_load, _ = previous_results[-1]
        if message_size > prev_message_size:
            initial_load = prev_threshold_load
    else:
        # Adjust initial load based on message size
        if message_size <= 1024:
            initial_load = 1 * 10**5
        elif message_size <= 4096:
            initial_load = 5 * 10**4
        else:
            initial_load = 2 * 10**4

    # initial_params = {
    #     "load": initial_load,

    initial_load = 1 * 10**5 if message_size <= 4096 else 1 * 10**4

    initial_params = {
        "load": initial_load,
        "message_size": message_size,
        "exp_name": exp_name,
        "exp_description": description,
    }
    rebind_parameters(durationSeconds=100)
    # Run a warmup
    exp(exp_name=exp_name, experiment_description="Warmup")
    test = ThresholdLoadTest(
        exp_name=exp_name,
        exp_description=description,
        executor=experiment,
        initial_params=initial_params,
    )
    final_history = test.execute()
    final_state = final_history.states[-1]
    final_result = final_history.results[-1]
    return final_state.params["load"], final_result.metrics["throughput"]


def threshold(exp_name: str, exp_description: str, message_sizes: list[int]) -> list[tuple[int, int]]:
    results = []
    for message_size in message_sizes:
        threshold_load, observed_throughput = find_threshold_load(
            exp_name=exp_name,
            message_size=message_size,
            description=exp_description,
        )
        results.append((threshold_load, observed_throughput))

        print(f"\nThreshold results for {exp_name}:")
        print(f"Message size: {message_size} bytes")
        print(f"Threshold load: {threshold_load} messages/second")
        print(f"Observed throughput: {observed_throughput} messages/second")

    return results
