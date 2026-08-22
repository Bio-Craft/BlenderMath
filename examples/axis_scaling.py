"""The same mathematical function under a changing coordinate unit size."""

from bmath import Axes, Create, MathTex, Scene, Style, Transform, YELLOW_C


class AxisScalingExample(Scene):
    def construct(self):
        axes = Axes(
            x_range=(-4, 4, 1), y_range=(-3, 3, 1), x_length=5.2, y_length=3.9,
            name="X Unit 1",
        )
        labels = axes.add_coordinates(label_type=MathTex)
        unit_label = MathTex('$ x " unit " = 1 $', name="X Unit Label 1").scale(.42).move_to((0, 0, 2.35))
        axes.add(unit_label)
        graph = axes.plot(
            "0.25*x**2 - 0.5", domain=(-4, 4),
            style=Style(color=YELLOW_C, width=0.012), name="Same Function",
        )
        larger_axes = Axes(
            x_range=(-8, 8, 2), y_range=(-3, 3, 1), x_length=5.2, y_length=3.9,
            name="X Unit 2",
        )
        larger_labels = larger_axes.add_coordinates(label_type=MathTex)
        larger_unit_label = MathTex('$ x " unit " = 2 $', name="X Unit Label 2").scale(.42).move_to((0, 0, 2.35))
        larger_axes.add(larger_unit_label)
        larger_graph = larger_axes.plot(
            "0.25*x**2 - 0.5", domain=(-4, 4),
            style=Style(color=YELLOW_C, width=0.012), name="Same Function Resampled",
        )
        self.play(Create(axes), run_time=1.5)
        self.play(Create(graph), run_time=1.0)
        self.play(Transform(axes, larger_axes), run_time=2.0)
        self.play(Transform(graph, larger_graph), run_time=2.0)
        self.wait(0.5)
