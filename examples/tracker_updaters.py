"""ValueTracker and scrubbable updater animation."""

from bmath import Create, Dot, NumberPlane, Scene, ValueTracker, linear


class TrackerUpdaterExample(Scene):
    def construct(self):
        plane = NumberPlane(x_range=(-4, 4, 1), y_range=(-1, 8, 1), x_length=8, y_length=5)
        graph = plane.plot(lambda x: x * x, domain=(-2.8, 2.8), name="f(x) = x^2")
        x = ValueTracker(-2, name="x")
        point = Dot(plane.c2p(x.value, x.value**2), name="Tracked Point")
        point.add_updater(lambda dot: dot.move_to(plane.c2p(x.value, x.value**2)))
        self.play(Create(plane), Create(graph), run_time=2)
        self.add(point)
        self.play(x.animate.set_value(2), run_time=4, rate_func=linear)
        self.wait(0.5)
