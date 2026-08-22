"""Reusable Geometry Nodes arrows and a procedural 3D axis triad."""

from bmath import Arrow3D, Create, Scene, Style, ThreeDAxes3D, YELLOW_C


class GeometryNodes3DExample(Scene):
    def construct(self):
        axes = ThreeDAxes3D(
            x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-2, 2, 1),
            x_length=5, y_length=5, z_length=5,
        )
        vector = Arrow3D(
            (0, 0, 0), (1.4, -1.1, 1.8),
            style=Style(color=YELLOW_C), name="Animated GN Vector",
        )
        self.play(Create(axes), Create(vector), run_time=1.2)
        self.play(
            vector.animate.put_start_and_end_on((-0.5, 0.2, -0.4), (2.0, 1.4, 0.8)),
            run_time=2.5,
        )
        self.wait(0.5)
