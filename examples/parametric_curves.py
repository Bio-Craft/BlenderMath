"""Parametric and polar graph helpers."""

import math

from bmath import Axes, Create, Scene, Style


class ParametricCurvesExample(Scene):
    def construct(self):
        axes = Axes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), x_length=6, y_length=6)
        lissajous = axes.plot_parametric(
            lambda t: (2.3 * math.sin(3 * t), 2.3 * math.sin(2 * t)),
            style=Style(color=(1, 0.3, 0.2, 1)),
            name="Lissajous Curve",
        )
        rose = axes.plot_polar(
            lambda theta: 1.8 * math.cos(5 * theta),
            style=Style(color=(0.2, 0.8, 0.45, 1)),
            name="Polar Rose",
        )
        self.play(Create(axes))
        self.play(Create(lissajous), Create(rose), run_time=3)
        self.wait(0.5)
