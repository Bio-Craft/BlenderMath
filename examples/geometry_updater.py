"""A continuous wave driven by a BMath ValueTracker."""

import math

from bmath import Axes, Polyline, Scene, Style, ValueTracker, WHITE, BLUE_C, linear


class GeometryUpdaterExample(Scene):
    def construct(self):
        axes = Axes(
            x_range=(0, 4, 1), y_range=(-1.5, 1.5, 1),
            x_length=8, y_length=3, include_axis_labels=False,
            style=Style(color=WHITE, width=0.01),
        )
        phase = ValueTracker(0, name="wave phase")
        xs = [4 * index / 95 for index in range(96)]
        wave = Polyline(
            [axes.c2p(x, math.sin(math.pi * x)) for x in xs],
            style=Style(color=BLUE_C, width=0.02), name="Live wave",
        )
        wave.add_updater(lambda curve: curve.set_points([
            axes.c2p(x, math.sin(math.pi * x - phase.value)) for x in xs
        ]))
        self.add(axes, wave)
        self.wait(1)
        self.play(phase.animate.set_value(4 * math.pi), run_time=6, rate_func=linear)
        self.wait(1)
