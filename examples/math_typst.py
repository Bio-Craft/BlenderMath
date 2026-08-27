"""MathTex/Typst example; requires blender_typst_importer in Blender."""

from bmath import BLUE_C, GREEN_C, MathTex, Scene, Transform, Write


class MathTypstExample(Scene):
    def construct(self):
        equation = MathTex(
            "$ integral_a^b f(x) dif x = F(b) - F(a) $",
            name="Semantic Integral Equation",
        )
        equation.set_color_by_token("integral", (1.0, 0.15, 0.08))
        equation.set_color_by_token("dif", (0.1, 0.45, 1.0))
        self.play(Write(equation), run_time=2)
        self.wait(0.5)
        rearranged = MathTex(
            "$ F(b) - F(a) = integral_a^b f(x) dif x $",
            name="Rearranged Integral Equation",
        )
        self.play(Transform(equation, rearranged), run_time=2)
        self.play(equation.animate(run_time=1.5).set_color(GREEN_C))
        self.wait(1)
        survival = MathTex(
            '$ l(a) = P("存活到年龄" a) $',
            name="CJK Compound Fill",
        )
        survival.set_color(BLUE_C)
        self.play(Transform(equation, survival), run_time=2)
        self.wait(1)
