"""Parallel animation, waits, and easing functions."""

from bmath import Circle, Create, Dot, Scene, ease_in_out_sine


class TimelineExample(Scene):
    def construct(self):
        slow = Dot((-3, 0, 1), name="Linear Dot")
        smooth = Circle(radius=0.25, name="Eased Circle").shift((-3, 0, -1))
        self.play(Create(slow), Create(smooth))
        self.wait(0.5)
        self.play(
            slow.animate(run_time=3, rate_func=lambda t: t).shift((6, 0, 0)),
            smooth.animate(run_time=3, rate_func=ease_in_out_sine).shift((6, 0, 0)),
        )
        self.wait(0.5)
