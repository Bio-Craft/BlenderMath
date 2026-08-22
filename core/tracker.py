"""Declarative scalar trackers compiled to Blender custom properties."""

from __future__ import annotations


class ValueTracker:
    def __init__(self, value: float = 0.0, name: str | None = None):
        self.value = float(value)
        self.name = name or "ValueTracker"

    def get_value(self) -> float:
        return self.value

    def set_value(self, value: float) -> "ValueTracker":
        self.value = float(value)
        return self

    @property
    def animate(self):
        tracker = self

        class Builder:
            def set_value(self, value):
                from .animation import TrackerAnimation
                return TrackerAnimation(tracker, value)

            to = set_value

        return Builder()
