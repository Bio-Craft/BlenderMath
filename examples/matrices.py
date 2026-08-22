"""Typst matrix/vector layout and transform example."""

from bmath import MathTex, Scene, Transform, Write


class MatricesExample(Scene):
    def construct(self):
        system = MathTex(
            "$ A = mat(2, 1; -1, 3) quad bold(x) = vec(x_1, x_2) $",
            name="Matrix And Vector",
        ).scale(0.9)
        product = MathTex(
            "$ A bold(x) = vec(2 x_1 + x_2, -x_1 + 3 x_2) $",
            name="Matrix Vector Product",
        ).scale(0.9)

        self.play(Write(system), run_time=2.5)
        self.wait(0.5)
        self.play(Transform(system, product), run_time=2.5)
        self.wait(1.0)
