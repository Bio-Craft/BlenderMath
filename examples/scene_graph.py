"""Nested local transforms: child rotation followed by parent motion."""

from bmath import Circle, Create, Dot, Line, Scene, Style, VGroup


class SceneGraphExample(Scene):
    def construct(self):
        rotor = VGroup(
            Line((0, 0, 0), (1.3, 0, 0), name="Child Arm"),
            Dot((1.3, 0, 0), radius=.13, name="Child Dot", style=Style(color=(1, .25, .15, 1))),
            name="Rotating Child Group",
        )
        system = VGroup(
            Circle(radius=1.3, name="Parent Boundary", style=Style(color=(.2, .65, 1, 1))),
            Dot(name="Parent Origin", radius=.11, style=Style(color=(1, .8, .1, 1))),
            rotor,
            name="Parent Group",
        )
        self.play(Create(system), run_time=2)
        self.play(rotor.animate.rotate(2.2), run_time=2)
        self.play(system.animate.shift((2, 0, .7)).scale(1.25), run_time=2)
        self.wait(0.5)
