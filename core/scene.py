"""Manim-style Scene orchestration and deterministic timeline planning."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable

from .animation import Animation, AnimationBuilder, TrackerAnimation, smoothstep
from .mobject import MObject


@dataclass
class TimelineClip:
    animation: object
    start_frame: int
    end_frame: int
    initial: object = None
    final: object = None
    initial_style: object = None
    final_style: object = None
    initial_geometry: object = None
    final_geometry: object = None


@dataclass
class BakedUpdaterClip:
    mobject: MObject
    samples: list[tuple[int, object]]


class Scene:
    fps = 30

    def __init__(self, name: str | None = None, fps: int | None = None):
        self.name = name or type(self).__name__
        self.fps = int(fps or self.fps)
        self.mobjects: list[MObject] = []
        self.timeline: list[TimelineClip] = []
        self.current_frame = 1
        self._constructed = False

    def construct(self):
        """Override in scene subclasses."""

    def build(self) -> "Scene":
        if not self._constructed:
            self.construct()
            self._constructed = True
        return self

    def add(self, *mobjects: MObject) -> "Scene":
        for mobject in mobjects:
            if any(mobject is member for root in self.mobjects for member in root.family()):
                continue
            family = tuple(mobject.family())
            self.mobjects = [root for root in self.mobjects if root not in family]
            self.mobjects.append(mobject)
        return self

    def remove(self, *mobjects: MObject) -> "Scene":
        for mobject in mobjects:
            if mobject in self.mobjects:
                self.mobjects.remove(mobject)
        return self

    def play(self, *animations, run_time: float | None = None, rate_func=None) -> "Scene":
        if not animations:
            return self
        built = []
        for item in animations:
            if isinstance(item, AnimationBuilder):
                item = item.build(run_time=run_time, rate_func=rate_func)
            if not isinstance(item, (Animation, TrackerAnimation)):
                raise TypeError(f"Expected Animation, got {type(item).__name__}")
            if run_time is not None:
                item.run_time = float(run_time)
            if rate_func is not None:
                item.rate_func = rate_func
            if isinstance(item, Animation):
                self.add(item.mobject)
            built.append(item)
        duration = max(item.run_time for item in built)
        end = self.current_frame + round(duration * self.fps)
        tracker_animations = [item for item in built if isinstance(item, TrackerAnimation)]
        updater_initial = {
            mobject.uid: deepcopy(mobject.state)
            for mobject in self.family()
            if mobject.updaters
        }
        clips = []
        for item in built:
            item_end = self.current_frame + round(item.run_time * self.fps)
            if isinstance(item, Animation):
                initial, final = item.states()
                if hasattr(item, "styles"):
                    initial_style, final_style = item.styles()
                else:
                    initial_style = final_style = deepcopy(item.mobject.style)
                if hasattr(item, "geometries"):
                    initial_geometry, final_geometry = item.geometries()
                else:
                    initial_geometry = final_geometry = deepcopy(item.mobject.geometry)
            else:
                initial, final = item.start_value, item.end_value
                initial_style = final_style = None
                initial_geometry = final_geometry = None
            clip = TimelineClip(
                item, self.current_frame, item_end, initial, final,
                initial_style, final_style, initial_geometry, final_geometry,
            )
            self.timeline.append(clip)
            clips.append(clip)
            item.finish()
        if tracker_animations and updater_initial:
            self._bake_updaters(tracker_animations, updater_initial, self.current_frame, end)
        else:
            self._run_updaters()
        self.current_frame = end
        return self

    def wait(self, duration: float = 1.0) -> "Scene":
        self.current_frame += round(float(duration) * self.fps)
        return self

    def _run_updaters(self):
        for root in self.mobjects:
            for mobject in root.family():
                for updater in mobject.updaters:
                    updater(mobject)

    def _bake_updaters(self, animations, initial_states, start, end):
        tracked = [(animation, animation.start_value) for animation in animations]
        targets = [mobject for mobject in self.family() if mobject.updaters]
        baked = {mobject.uid: [] for mobject in targets}
        for frame in range(start, end + 1):
            for animation, _ in tracked:
                span = max(1, round(animation.run_time * self.fps))
                t = max(0.0, min(1.0, (frame - start) / span))
                t = animation.rate_func(t)
                animation.tracker.value = animation.start_value + t * (animation.end_value - animation.start_value)
            for mobject in targets:
                mobject.state = deepcopy(initial_states[mobject.uid])
                for updater in mobject.updaters:
                    updater(mobject)
                baked[mobject.uid].append((frame, deepcopy(mobject.state)))
        for animation, _ in tracked:
            animation.tracker.value = animation.end_value
        for mobject in targets:
            self.timeline.append(BakedUpdaterClip(mobject, baked[mobject.uid]))

    @property
    def frame_end(self):
        return max(1, self.current_frame)

    def family(self):
        seen = set()
        for root in self.mobjects:
            for mobject in root.family():
                if mobject.uid not in seen:
                    seen.add(mobject.uid)
                    yield mobject


# Compatibility models for data-only callers from the first prototype.
from .mobject import Style as PlotStyle  # noqa: E402
from .geometry import Polyline as Series  # noqa: E402
