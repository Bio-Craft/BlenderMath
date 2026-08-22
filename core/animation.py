"""Timeline-safe animation primitives and Manim-style animate builder."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .mobject import MObject, TransformState
    from .tracker import ValueTracker

RateFunction = Callable[[float], float]


def linear(t: float) -> float:
    return t


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1.0) / 2.0


@dataclass(frozen=True)
class Keyframe:
    frame: int
    value: float


class Animation:
    """Base animation; subclasses describe end state without touching Blender."""

    def __init__(self, mobject: "MObject", run_time: float = 1.0, rate_func: RateFunction = smoothstep):
        self.mobject = mobject
        self.run_time = float(run_time)
        self.rate_func = rate_func
        if self.run_time < 0:
            raise ValueError("run_time cannot be negative")

    def states(self) -> tuple["TransformState", "TransformState"]:
        start = deepcopy(self.mobject.state)
        return start, deepcopy(start)

    def finish(self) -> None:
        self.mobject.state = self.states()[1]


class StateAnimation(Animation):
    def __init__(self, mobject: "MObject", end_state: "TransformState", end_style=None, end_geometry=None, **kwargs):
        super().__init__(mobject, **kwargs)
        self.end_state = deepcopy(end_state)
        self.end_style = deepcopy(end_style if end_style is not None else mobject.style)
        self.end_geometry = deepcopy(end_geometry if end_geometry is not None else mobject.geometry)

    def states(self):
        return deepcopy(self.mobject.state), deepcopy(self.end_state)

    def styles(self):
        return deepcopy(self.mobject.style), deepcopy(self.end_style)

    def geometries(self):
        return deepcopy(self.mobject.geometry), deepcopy(self.end_geometry)

    def finish(self):
        self.mobject.state = deepcopy(self.end_state)
        self.mobject.style = deepcopy(self.end_style)
        self.mobject.geometry = deepcopy(self.end_geometry)


class Create(Animation):
    def states(self):
        start = deepcopy(self.mobject.state)
        end = deepcopy(start)
        start.draw_progress = 0.0
        start.opacity = 1.0
        start.visible = True
        end.draw_progress = 1.0
        end.opacity = 1.0
        end.visible = True
        return start, end


class Write(Create):
    pass


class FadeIn(Animation):
    def states(self):
        start = deepcopy(self.mobject.state)
        end = deepcopy(start)
        start.opacity = 0.0
        start.visible = True
        end.opacity = 1.0
        return start, end


class FadeOut(Animation):
    def states(self):
        start = deepcopy(self.mobject.state)
        end = deepcopy(start)
        end.opacity = 0.0
        end.visible = False
        return start, end


class MoveTo(StateAnimation):
    def __init__(self, mobject, point, **kwargs):
        clone = mobject.copy().move_to(point)
        super().__init__(mobject, clone.state, **kwargs)


class Rotate(StateAnimation):
    def __init__(self, mobject, angle: float, axis: str = "Y", about_point=None, **kwargs):
        clone = mobject.copy().rotate(angle, axis, about_point=about_point)
        super().__init__(mobject, clone.state, **kwargs)


class Scale(StateAnimation):
    def __init__(self, mobject, factor, about_point=None, **kwargs):
        clone = mobject.copy().scale(factor, about_point=about_point)
        super().__init__(mobject, clone.state, **kwargs)


class Transform(StateAnimation):
    def __init__(self, mobject, target, path_arc: float = 0.0, path_func=None, **kwargs):
        super().__init__(mobject, target.state, end_style=target.style, **kwargs)
        self.target = target
        self.path_arc = float(path_arc)
        self.path_func = path_func
        self.child_morphs = []
        self.child_math_transforms = []
        self._collect_child_morphs(mobject, target)

    def _collect_child_morphs(self, source, target):
        if source is not self.mobject and source.kind == "math" and target.kind == "math":
            self.child_math_transforms.append(Transform(
                source, target, path_arc=self.path_arc, path_func=self.path_func,
                run_time=self.run_time, rate_func=self.rate_func,
            ))
            return
        if source.geometry.get("points") is not None and target.geometry.get("points") is not None:
            self.child_morphs.append((
                source,
                deepcopy(source.geometry), deepcopy(target.geometry),
                deepcopy(source.state), deepcopy(target.state),
                deepcopy(source.style), deepcopy(target.style),
            ))
        if source.children or target.children:
            if len(source.children) != len(target.children):
                if source.kind == "function_graph" and target.kind == "function_graph":
                    raise ValueError("FunctionGraph morph currently requires equal curve segment counts")
                return
            for source_child, target_child in zip(source.children, target.children):
                self._collect_child_morphs(source_child, target_child)

    def geometries(self):
        return deepcopy(self.mobject.geometry), deepcopy(self.target.geometry)

    def finish(self):
        super().finish()
        self.mobject.geometry = deepcopy(self.target.geometry)
        for source, _geometry, target_geometry, _state, target_state, _style, target_style in self.child_morphs:
            if source is self.mobject:
                continue
            source.geometry = deepcopy(target_geometry)
            source.state = deepcopy(target_state)
            source.style = deepcopy(target_style)
        for child_animation in self.child_math_transforms:
            child_animation.finish()


class TransformMatchingTex(Transform):
    """Move equal Typst parts between formulas and fade unmatched parts."""

    def __init__(
        self,
        mobject,
        target,
        *,
        key_map=None,
        align_token=None,
        path_arc: float = 0.0,
        path_func=None,
        **kwargs,
    ):
        if mobject.kind != "math" or target.kind != "math":
            raise TypeError("TransformMatchingTex requires two MathTex objects")
        self.key_map = dict(key_map or {})
        self.align_token = align_token
        super().__init__(
            mobject, target, path_arc=path_arc, path_func=path_func, **kwargs,
        )

    def matching_parts(self):
        return self.mobject.matching_parts(self.target, self.key_map)


MatchTermTransform = TransformMatchingTex


class TrackerAnimation:
    def __init__(self, tracker: "ValueTracker", value: float, run_time: float = 1.0, rate_func: RateFunction = smoothstep):
        self.tracker = tracker
        self.start_value = tracker.value
        self.end_value = float(value)
        self.run_time = float(run_time)
        self.rate_func = rate_func

    def finish(self):
        self.tracker.value = self.end_value


class AnimationBuilder:
    """Records chained mutations without mutating the source object."""

    def __init__(self, mobject: "MObject"):
        self.mobject = mobject
        self.target = mobject.copy()
        self.run_time = None
        self.rate_func = None

    def __call__(self, *, run_time=None, rate_func=None):
        self.run_time = run_time
        self.rate_func = rate_func
        return self

    def __getattr__(self, name):
        method = getattr(self.target, name)

        def mutate(*args, **kwargs):
            method(*args, **kwargs)
            return self
        return mutate

    def build(self, run_time=None, rate_func=None) -> StateAnimation:
        return StateAnimation(
            self.mobject,
            self.target.state,
            end_style=self.target.style,
            end_geometry=self.target.geometry,
            run_time=run_time if run_time is not None else (self.run_time if self.run_time is not None else 1.0),
            rate_func=rate_func if rate_func is not None else (self.rate_func or smoothstep),
        )


class LegacyAnimation:
    """Scalar interpolation retained for compatibility with the initial API."""

    def __init__(self, *keyframes: Keyframe, easing: RateFunction = smoothstep):
        if not keyframes:
            raise ValueError("Animation needs at least one keyframe")
        self.keyframes = tuple(sorted(keyframes, key=lambda item: item.frame))
        if len({item.frame for item in self.keyframes}) != len(self.keyframes):
            raise ValueError("Keyframe frames must be unique")
        self.easing = easing

    def value_at(self, frame: int) -> float:
        if frame <= self.keyframes[0].frame:
            return self.keyframes[0].value
        if frame >= self.keyframes[-1].frame:
            return self.keyframes[-1].value
        for left, right in zip(self.keyframes, self.keyframes[1:]):
            if left.frame <= frame <= right.frame:
                t = self.easing((frame - left.frame) / (right.frame - left.frame))
                return left.value + t * (right.value - left.value)
        raise RuntimeError("Unreachable interval")
