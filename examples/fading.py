"""Independent fade-in and fade-out animations."""

from bmath import Circle, FadeIn, FadeOut, Rectangle, Scene


class FadingExample(Scene):
    def construct(self):
        circle = Circle(name="Fade In Circle").shift((-1.3, 0, 0))
        rectangle = Rectangle(name="Fade Out Rectangle").shift((1.3, 0, 0))
        self.add(rectangle)
        self.play(FadeIn(circle), FadeOut(rectangle), run_time=1.5)
        self.play(FadeOut(circle), FadeIn(rectangle), run_time=1.5)
        self.wait(0.5)
