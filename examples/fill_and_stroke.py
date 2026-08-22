"""Independent fill and stroke materials on closed planar geometry."""

from bmath import BLUE_D, GREEN_D, RED_C, YELLOW_D, Circle, Create, Rectangle, Scene, Style


class FillAndStrokeExample(Scene):
    def construct(self):
        circle = Circle(
            radius=1.2,
            name="Coral Fill Blue Stroke",
            style=Style(
                color=BLUE_D,
                width=0.045,
                fill_color=RED_C,
                fill_opacity=0.65,
            ),
        ).shift((-1.8, 0, 0))
        rectangle = Rectangle(
            width=2.4,
            height=1.8,
            name="Green Fill Yellow Stroke",
            style=Style(
                color=YELLOW_D,
                width=0.04,
                fill_color=GREEN_D,
                fill_opacity=0.5,
            ),
        ).shift((1.8, 0, 0))
        self.play(Create(circle), Create(rectangle), run_time=2.5)
        self.play(circle.animate.rotate(0.7).scale(1.2), rectangle.animate.rotate(-0.7), run_time=2)
        self.wait(0.5)
