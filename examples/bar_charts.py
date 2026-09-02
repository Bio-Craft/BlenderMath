"""2D Grease Pencil bars and Riemann rectangles derived from one axes."""

from math import exp

from bmath import Axes, BLUE_C, Create, FadeOut, ORANGE, Scene, Style


class BarChartsExample(Scene):
    def construct(self):
        axes = Axes(
            x_range=(0, 6, 1),
            y_range=(0, 1.2, 0.2),
            x_length=9,
            y_length=4.5,
            include_axis_labels=False,
        )
        curve = axes.plot(
            lambda x: x * exp(-x),
            domain=(0, 6),
            style=Style(color=ORANGE, width=0.012),
        )
        coarse = axes.get_riemann_rectangles(
            lambda x: x * exp(-x),
            x_range=(0, 6),
            dx=0.75,
            gap_ratio=0.08,
            style=Style(
                color=BLUE_C, width=0.004,
                fill_color=BLUE_C, fill_opacity=0.8,
            ),
        )
        fine = axes.get_riemann_rectangles(
            lambda x: x * exp(-x),
            x_range=(0, 6),
            dx=0.15,
            style=Style(
                color=BLUE_C, width=0.002,
                fill_color=BLUE_C, fill_opacity=0.8,
            ),
        )
        for chart in (coarse, fine):
            chart.scale_y(0.001, about_point=chart.baseline_point).set_opacity(0)

        self.play(Create(axes), Create(curve), run_time=1.5)
        self.play(
            coarse.animate.scale_y(1000, about_point=coarse.baseline_point).set_opacity(1),
            run_time=1.0,
        )
        self.wait(0.5)
        self.play(
            FadeOut(coarse),
            fine.animate.scale_y(1000, about_point=fine.baseline_point).set_opacity(1),
            run_time=1.0,
        )
        self.wait(0.75)
