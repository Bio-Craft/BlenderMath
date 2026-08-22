"""Adaptive plotting and discontinuity splitting."""

import math

from bmath import BLUE_D, GREEN_C, RED_C, Axes, Create, Scene, Style, Transform


class FunctionGraphsExample(Scene):
    def construct(self):
        axes = Axes(x_range=(-6, 6, 1), y_range=(-3, 3, 1), x_length=10, y_length=5)
        sine = axes.plot(math.sin, style=Style(color=BLUE_D), name="sin(x)")
        reciprocal = axes.plot(lambda x: 1 / x, domain=(-5, 5), style=Style(color=RED_C), name="1/x")
        oscillation = axes.plot(lambda x: 0.3 * math.sin(12 * x) - 2, tolerance=0.005, name="High Frequency")
        self.play(Create(axes))
        self.play(Create(sine), Create(reciprocal), Create(oscillation), run_time=3)
        parabola = axes.plot(
            lambda x: 0.12 * x * x - 1.5,
            style=Style(color=GREEN_C, width=.04),
            name="0.12x^2 - 1.5",
        )
        self.play(Transform(sine, parabola), run_time=3)
        self.wait(0.5)
