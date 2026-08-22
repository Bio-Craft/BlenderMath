"""Chained method animation and explicit transform helpers."""

import math

from bmath import BLUE_D, GREEN_C, Circle, Create, Rectangle, Transform, Scene, Style


class TransformationsExample(Scene):
    def construct(self):
        style = Style(color=BLUE_D, width=0.035, fill_color=BLUE_D, fill_opacity=.2)
        straight = Circle(radius=0.35, name="Linear Transform", style=style).move_to((-3, 0, 1.5))
        arc = Circle(radius=0.35, name="Arc Transform", style=style).move_to((-3, 0, 0))
        wave = Circle(radius=0.35, name="Custom Path Transform", style=style).move_to((-3, 0, -1.5))
        self.play(Create(straight), Create(arc), Create(wave))

        def wave_path(start, end, t):
            return (
                start[0] + (end[0] - start[0]) * t,
                0,
                start[2] + (end[2] - start[2]) * t + 0.65 * math.sin(math.tau * t),
            )

        self.play(
            Transform(
                straight,
                Rectangle(width=1.5, height=.9, name="Rectangle Target", style=Style(
                    color=GREEN_C, width=.05, fill_color=GREEN_C, fill_opacity=.5,
                )).move_to((3, 0, 1.5)),
                path_arc=0,
            ),
            Transform(arc, arc.copy().move_to((3, 0, 0)), path_arc=math.pi / 2),
            Transform(wave, wave.copy().move_to((3, 0, -1.5)), path_func=wave_path),
            run_time=3,
        )
        self.wait(0.5)
