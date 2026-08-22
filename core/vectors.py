"""Tiny vector helpers kept dependency-free for Blender and notebooks."""

from __future__ import annotations

from collections.abc import Iterable
import math

Vec3 = tuple[float, float, float]


def vec3(value: Iterable[float] | Vec3) -> Vec3:
    values = tuple(float(item) for item in value)
    if len(values) == 2:
        return values[0], values[1], 0.0
    if len(values) != 3:
        raise ValueError("Expected a 2D or 3D vector")
    return values  # type: ignore[return-value]


def add(left: Vec3, right: Vec3) -> Vec3:
    return tuple(a + b for a, b in zip(left, right))  # type: ignore[return-value]


def sub(left: Vec3, right: Vec3) -> Vec3:
    return tuple(a - b for a, b in zip(left, right))  # type: ignore[return-value]


def mul(value: Vec3, scalar: float) -> Vec3:
    return tuple(item * scalar for item in value)  # type: ignore[return-value]


def length(value: Vec3) -> float:
    return math.sqrt(sum(item * item for item in value))


ORIGIN: Vec3 = (0.0, 0.0, 0.0)
RIGHT: Vec3 = (1.0, 0.0, 0.0)
LEFT: Vec3 = (-1.0, 0.0, 0.0)
UP: Vec3 = (0.0, 0.0, 1.0)
DOWN: Vec3 = (0.0, 0.0, -1.0)
OUT: Vec3 = (0.0, 1.0, 0.0)
