"""Native Grease Pencil creation followed by method-style animations."""

import math

from bmath import Arrow, Circle, Create, Line, Rectangle, Scene, Style


class CreationExample(Scene):
    def construct(self):
        circle = Circle(
            radius=0.9,
            name="Circle",
            style=Style(color=(0.1, 0.55, 1.0, 1.0), fill_color=(0.0, 0.8, 0.9, 1.0), fill_opacity=0.35),
        ).shift((-2.3, 0, 0))
        square = Rectangle(
            width=1.7,
            height=1.7,
            name="Square",
            style=Style(color=(1.0, 0.75, 0.1, 1.0), fill_color=(1.0, 0.25, 0.15, 1.0), fill_opacity=0.4),
        ).shift((2.3, 0, 0))
        baseline = Line((-4.0, 0, -1.5), (4.0, 0, -1.5), name="Baseline")
        direction = Arrow((-0.8, 0, 1.45), (0.8, 0, 1.45), name="Direction")

        self.play(Create(circle), Create(square), Create(baseline), Create(direction), run_time=2)
        self.play(
            circle.animate(run_time=2).shift((1.2, 0, 0.55)).scale(1.25).set_color((0.2, 1.0, 0.4, 1.0)),
            square.animate(run_time=2).shift((-1.2, 0, -0.1)).rotate(math.pi / 3).set_fill((0.65, 0.2, 1.0, 1.0), 0.75),
        )
        self.play(
            circle.animate(run_time=1.5).shift((-0.6, 0, -0.8)),
            square.animate(run_time=1.5).shift((0.8, 0, 0.65)).set_stroke((1.0, 1.0, 1.0, 1.0), 0.09),
        )
        self.wait(1)
