"""A semantic Typst derivation of the quadratic formula."""

from bmath import (
    BLUE_C, YELLOW_C, MathTex, Scene, TransformMatchingTex, Write,
)


class QuadraticDerivationExample(Scene):
    def construct(self):
        title = MathTex('#text(size: 18pt)[Quadratic formula]').move_to((0, 0, 2.25))
        self.play(Write(title), run_time=1.0)

        sources = (
            "$ a x^2 + b x + c = 0 $",
            "$ 4 a^2 x^2 + 4 a b x = -4 a c $",
            "$ (2 a x + b)^2 = b^2 - 4 a c $",
            "$ 2 a x + b = plus.minus sqrt(b^2 - 4 a c) $",
            "$ x = (-b plus.minus sqrt(b^2 - 4 a c)) / (2 a) $",
        )

        def equation(source):
            result = MathTex(
                source,
                substrings_to_isolate=("plus.minus", "sqrt(b^2 - 4 a c)"),
                stroke_mode="NONE",
            ).scale(0.92)
            result.set_color_by_token("x", BLUE_C)
            for coefficient in ("a", "b", "c"):
                result.set_color_by_token(coefficient, YELLOW_C)
            return result

        current = equation(sources[0])
        self.play(Write(current), run_time=1.8)
        self.wait(0.35)

        for source in sources[1:]:
            target = equation(source)
            self.play(
                TransformMatchingTex(
                    current,
                    target,
                    path_arc=0.12,
                ),
                run_time=1.8,
            )
            self.wait(0.3)

        self.wait(1.0)
