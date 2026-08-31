"""Stable matrix cells, semantic colors, and vector layout."""

from bmath import BLUE_C, ORANGE, MathMatrix, MathTex, Scene, VGroup, Write


class MatricesExample(Scene):
    def construct(self):
        matrix = MathMatrix(
            (("b_0", "b_1"), ("s_0", "0")),
            element_colors={"b_0": ORANGE, "b_1": ORANGE, "s_0": BLUE_C},
            name="Semantically Colored Matrix",
        )
        vector = MathMatrix((("n_0",), ("n_1",)), name="Population Vector")
        system = VGroup(
            MathTex("$ L = $"), matrix, vector,
            name="Matrix And Vector",
        ).arrange(buff=0.22)

        self.play(Write(system), run_time=2.0)
        self.wait(1.0)
