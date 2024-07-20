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
