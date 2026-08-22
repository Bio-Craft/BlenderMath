"""Bounds-aware layout operations on differently sized objects."""

from bmath import BLUE_D, GREEN_C, RED_C, UP, Circle, Create, FadeIn, Rectangle, Scene, Style, Text, VGroup


class SpatialLayoutExample(Scene):
    def construct(self):
        title = Text("Bounds-aware layout", font_size=.42).to_edge(UP, buff=.35)
        row = VGroup(
            Circle(radius=.45, style=Style(color=BLUE_D, fill_color=BLUE_D, fill_opacity=.25)),
            Rectangle(width=2.1, height=.8, style=Style(color=GREEN_C, fill_color=GREEN_C, fill_opacity=.25)),
            Circle(radius=.7, style=Style(color=RED_C, fill_color=RED_C, fill_opacity=.25)),
            name="Size-aware Row",
        ).arrange(buff=.35)
        grid = VGroup(*(
            Rectangle(width=.7 + .25 * index, height=.55 + .1 * (index % 2), name=f"Grid Cell {index + 1}")
            for index in range(6)
        ), name="Adaptive Grid").arrange_in_grid(rows=2, cols=3, buff=(.3, .35))
        grid.next_to(row, (0, 0, -1), buff=.75)

        self.play(FadeIn(title), Create(row), run_time=1.5)
        self.play(Create(grid), run_time=1.5)
        self.wait(1)
