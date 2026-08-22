"""Lightweight deterministic ODE simulation for visualization workflows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

State = tuple[float, ...]
Derivative = Callable[[float, State], Sequence[float]]


def rk4(function: Derivative, time: float, state: State, step: float) -> State:
    def shifted(scale: float, delta: Sequence[float]) -> State:
        return tuple(value + scale * change for value, change in zip(state, delta))

    k1 = tuple(function(time, state))
    k2 = tuple(function(time + step / 2, shifted(step / 2, k1)))
    k3 = tuple(function(time + step / 2, shifted(step / 2, k2)))
    k4 = tuple(function(time + step, shifted(step, k3)))
    return tuple(
        value + step * (a + 2 * b + 2 * c + d) / 6
        for value, a, b, c, d in zip(state, k1, k2, k3, k4)
    )


@dataclass
class Simulation:
    derivative: Derivative
    initial_state: State
    start: float = 0.0

    def solve(self, duration: float, step: float) -> list[tuple[float, State]]:
        if duration < 0 or step <= 0:
            raise ValueError("duration must be non-negative and step must be positive")
        time = self.start
        state = tuple(float(value) for value in self.initial_state)
        result = [(time, state)]
        target = self.start + duration
        while time < target:
            actual_step = min(step, target - time)
            state = rk4(self.derivative, time, state, actual_step)
            time += actual_step
            result.append((time, state))
        return result
