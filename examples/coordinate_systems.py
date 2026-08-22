"""Axes, NumberPlane, and c2p coordinate conversion."""

from bmath import Axes, Create, Dot, NumberLine, NumberPlane, Scene, ThreeDAxes, VGroup


class CoordinateSystemsExample(Scene):
    def construct(self):
        axes = Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=5, y_length=3).shift((-3, 0, 0))
        axes.add_coordinates()
        plane = NumberPlane(
            x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=5, y_length=3,
            axis_labels=("u", "v"),
        ).shift((3, 0, 0))
        plane.add_coordinates(x_values=(-2, 2), y_values=(-1, 1))
        points = VGroup(
            Dot(axes.c2p(1, 1), name="Axes c2p(1, 1)"),
            Dot(plane.c2p(-2, -1), name="Plane c2p(-2, -1)"),
            name="Coordinate Points",
        )
        number_line = NumberLine(x_range=(-3, 3, 1), length=5, include_numbers=True, name="Number Line").shift((0, 0, -2.4))
        axes_3d = ThreeDAxes(
            x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-2, 2, 1),
            unit_size=.65, name="3D Axes",
        ).shift((0, 0, 2.8))
        self.play(Create(axes), Create(plane), run_time=2)
        self.play(Create(points), Create(number_line), run_time=0.8)
        self.play(Create(axes_3d), run_time=1.2)
        self.wait(0.5)
