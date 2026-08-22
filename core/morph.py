"""Dependency-free point correspondence for curve morphing."""

from __future__ import annotations

import math

from .vectors import Vec3, length, sub


def resample_curve(points, count: int, *, cyclic: bool) -> list[Vec3]:
    """Sample a polyline at equal arc-length intervals."""
    values = [tuple(map(float, point)) for point in points]
    if len(values) < 2 or count < 2:
        raise ValueError("Curve resampling needs at least two points and samples")
    segments = list(zip(values, values[1:]))
    if cyclic:
        segments.append((values[-1], values[0]))
    lengths = [length(sub(right, left)) for left, right in segments]
    total = sum(lengths)
    if total <= 1e-12:
        return [values[0]] * count
    distances = [total * index / (count if cyclic else count - 1) for index in range(count)]
    result = []
    segment_index = 0
    consumed = 0.0
    for distance in distances:
        while segment_index < len(segments) - 1 and consumed + lengths[segment_index] < distance:
            consumed += lengths[segment_index]
            segment_index += 1
        left, right = segments[segment_index]
        segment_length = lengths[segment_index]
        amount = 0.0 if segment_length <= 1e-12 else (distance - consumed) / segment_length
        result.append(tuple(a + (b - a) * amount for a, b in zip(left, right)))
    return result


def align_curve_points(source, target, *, cyclic: bool) -> list[Vec3]:
    """Choose target direction and, for loops, start index with least travel."""
    source = list(source)
    target = list(target)
    if len(source) != len(target):
        raise ValueError("Aligned curves must have equal point counts")

    def cost(candidate):
        return sum(sum((a - b) ** 2 for a, b in zip(left, right)) for left, right in zip(source, candidate))

    if not cyclic:
        reversed_target = list(reversed(target))
        return reversed_target if cost(reversed_target) < cost(target) else target
    candidates = []
    for values in (target, list(reversed(target))):
        candidates.extend(values[offset:] + values[:offset] for offset in range(len(values)))
    return min(candidates, key=cost)


def prepare_morph_points(source, target, *, cyclic: bool, count: int | None = None):
    sample_count = count or max(len(source), len(target), 64 if cyclic else 2)
    start = resample_curve(source, sample_count, cyclic=cyclic)
    end = resample_curve(target, sample_count, cyclic=cyclic)
    return start, align_curve_points(start, end, cyclic=cyclic)


def interpolate_points(source, target, amount: float):
    return [tuple(a + (b - a) * amount for a, b in zip(left, right)) for left, right in zip(source, target)]


def sample_cubic_bezier_path(
    points,
    left_handles,
    right_handles,
    *,
    cyclic: bool,
    resolution: int = 8,
) -> list[Vec3]:
    """Flatten a cubic Bezier path without treating its anchors as a polyline."""
    anchors = [tuple(map(float, point)) for point in points]
    left = [tuple(map(float, point)) for point in left_handles]
    right = [tuple(map(float, point)) for point in right_handles]
    if len(anchors) < 2 or len(left) != len(anchors) or len(right) != len(anchors):
        raise ValueError("Bezier anchors and handles must have equal lengths")
    resolution = max(1, int(resolution))
    segment_count = len(anchors) if cyclic else len(anchors) - 1
    result = [anchors[0]]
    for index in range(segment_count):
        next_index = (index + 1) % len(anchors)
        p0, p1 = anchors[index], right[index]
        p2, p3 = left[next_index], anchors[next_index]
        for step in range(1, resolution + 1):
            if cyclic and index == segment_count - 1 and step == resolution:
                continue
            amount = step / resolution
            inverse = 1.0 - amount
            result.append(tuple(
                inverse ** 3 * a
                + 3.0 * inverse ** 2 * amount * b
                + 3.0 * inverse * amount ** 2 * c
                + amount ** 3 * d
                for a, b, c, d in zip(p0, p1, p2, p3)
            ))
    return result
