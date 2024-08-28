import contextlib
from typing import Callable, NamedTuple, Any
import pendulum
import os
import logging


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


class ThresholdResult(NamedTuple):
    messageSize: int
    threshold_load: int
    observed_throughput: int
    history: History


def decide(history: History) -> Decision | None:
    """
    This function looks at how the experiment has been going so far
    and decides what to do next. It returns a Decision object with the
    next parameters to try, or None if the experiment should be stopped.
    """
    if not history.states:
        # Can't make a decision without any data, this
        # should never happen
        raise

    # This is a simple binary search algorithm to find the threshold load
    # it only needs the last state and result to make a decision

    prev_params = history.states[-1].params
    prev_metrics = history.results[-1].metrics

    load = prev_params["load"]
    throughput = prev_metrics["throughput"]

    threshold = 0.05
    ableToHandle = throughput >= load * (1 - threshold)

    low = prev_params["low"]
    high = prev_params["high"]

    if high is None:
        if not ableToHandle:
            high = throughput
            new_load = (low + high) // 2
            return Decision(
                next_params={
                    **prev_params,
                    "load": new_load,
                    "high": high,
                }
            )
        else:
            # Double the load until failure
            new_load = load * 2
            return Decision(
                next_params={
                    **prev_params,
                    "load": new_load,
                    "low": load,
                }
            )
    else:
        if ableToHandle:
            if high - low < load * 0.05:
                logging.info({"msg": "Converged"})
                # The range is small enough, we can stop the experiment
                return None
            # It was able to handle the load
            # So we can set this as the new low
            low = load
            new_load = (low + high) // 2
            return Decision(
                next_params={
                    **prev_params,
                    "load": new_load,
                    "low": low,
                }
            )
        else:
            high = min(high, load)  # Ensure high is not increased
            if low == get_lower_bound(prev_params["messageSize"]):
                # Heuristic to hopefully get faster convergence
                # If low is still the default value, set it based on observed throughput
                low = throughput * 0.8
            # if low > high:
            #     low = high * 0.9
            new_load = (low + high) // 2
            return Decision(
                next_params={
                    **prev_params,
                    "load": new_load,
                    "high": high,
                    "low": low,
                }
            )


def execute(initial_params: dict[str, Any]) -> History:
    history = History(states=[], results=[])
    max_iterations = 15

    def recurse(
        history: History,
        params: dict[str, Any],
        it: int,
        max_iterations: int = max_iterations,
    ) -> History:
        if it >= max_iterations:
            logging.warning("Max iterations reached")
            return history

        state = State(params=params, time=pendulum.now())
        result = experiment(state)

        new_history = History(
            states=history.states + [state], results=history.results + [result]
        )

        decision = decide(new_history)
        if decision is None:
            return new_history

        return recurse(new_history, decision.next_params, it + 1)

    return recurse(history, initial_params, 0)


def experiment(state: State) -> Result:
    from greenflow.exp_ng.exp_ng import exp
    from greenflow.analysis import get_observed_throughput_of_last_experiment
    from entrypoint import rebind_parameters

    params = state.params

    load = int(params["load"])
    messageSize = int(params["messageSize"])
    start_time = pendulum.now()
    rebind_parameters(load=load, messageSize=messageSize)
    # exp is calling ansible_runner
    # Its output is very verbose, so we are not printing it
    # Suppress stdout and stderr before calling exp
    logging.warning(
        {
            "msg": "Starting",
            **params,
            "messageSize": messageSize,
            "load": load,
        }
    )
    exp(
        experiment_description=params["exp_description"],
    )
    throughput = get_observed_throughput_of_last_experiment(
        minimum_current_ts=start_time
    )
    return Result(metrics={"throughput": throughput}, time=state.time)

def get_lower_bound(messageSize: int) -> int:
    if messageSize == 128:
        return 2 * 10**6
    elif messageSize <= 4096:
        return 5 * 10**4
    else:
        return 1 * 10**4

def threshold(
    exp_name: str, exp_description: str, messageSizes: list[int]
) -> list[ThresholdResult]:
    from .exp_ng.exp_ng import exp

    results = []

    from entrypoint import rebind_parameters

    rebind_parameters(durationSeconds=10)
    exp(experiment_description="Warmup")
    rebind_parameters(durationSeconds=100)
    first_messageSize = messageSizes[0]

    initial_params = {
        "messageSize": first_messageSize,
        "exp_name": exp_name,
        "exp_description": exp_description,
        "low": get_lower_bound(first_messageSize),
        "load": get_lower_bound(first_messageSize),
        "high": None,
    }
    first_history = execute(initial_params=initial_params)
    first_final_state = first_history.states[-1]
    first_final_result = first_history.results[-1]
    results.append(
        ThresholdResult(
            messageSize=first_messageSize,
            threshold_load=first_final_state.params["load"],
            observed_throughput=first_final_result.metrics["throughput"],
            history=first_history,
        )
    )

    for messageSize in messageSizes[1:]:
        high = results[-1].threshold_load
        low = get_lower_bound(messageSize)
        if high < low:
            # swap low and high
            high = low
            low = 0
        initial_params = initial_params | {
            "low": low,
            "load": (low + high) // 2,
            "high": high,
            "messageSize": messageSize,
        }
        history = execute(initial_params=initial_params)
        last_state = history.states[-1]
        last_result = history.results[-1]
        threshold_result = ThresholdResult(
            messageSize=messageSize,
            threshold_load=last_state.params["load"],
            observed_throughput=last_result.metrics["throughput"],
            history=history,
        )
        # logging.info({"exp_name": exp_name, "result": threshold_result})
        results.append(threshold_result)

    return results


def threshold_primed(
    exp_name: str, exp_description: str, messageSizes: list[int]
) -> list[ThresholdResult]:
    from greenflow.playbook import exp

    from entrypoint import rebind_parameters

    rebind_parameters(durationSeconds=10)
    exp(experiment_description="Warmup")
    rebind_parameters(durationSeconds=100)

    results = [
        ThresholdResult(
            messageSize=128,
            threshold_load=3917060,
            observed_throughput=3758691,
            history=History(states=[], results=[]),
        ),
        ThresholdResult(
            messageSize=512,
            threshold_load=1386134,
            observed_throughput=1375417,
            history=History(states=[], results=[]),
        ),
        ThresholdResult(
            messageSize=1024,
            threshold_load=712266,
            observed_throughput=706587,
            history=History(states=[], results=[]),
        ),
        ThresholdResult(
            messageSize=2048,
            threshold_load=341127,
            observed_throughput=335415,
            history=History(states=[], results=[]),
        ),
    ]

    initial_params = {
        "messageSize": results[-1].messageSize,
        "exp_name": exp_name,
        "exp_description": exp_description,
        "low": get_lower_bound(results[-1].messageSize),
        "load": get_lower_bound(results[-1].messageSize),
    }


    for messageSize in messageSizes[3:]:
        high = results[-1].threshold_load
        low = get_lower_bound(messageSize)
        initial_params = initial_params | {
            "low": low,
            "load": (low + high) // 2,
            "high": high,
            "messageSize": messageSize,
        }
        history = execute(initial_params=initial_params)
        last_state = history.states[-1]
        last_result = history.results[-1]
        threshold_result = ThresholdResult(
            messageize=messageSize,
            threshold_load=last_state.params["load"],
            observed_throughput=last_result.metrics["throughput"],
            history=history,
        )
        # logging.info({"exp_name": exp_name, "result": threshold_result})
        results.append(threshold_result)

    return results
