"""Numerical simulation cache visualized as a native animated trajectory."""

from bmath import Create, Polyline, Scene, Simulation, Style


class SimulationExample(Scene):
    def construct(self):
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0

        def lorenz(_time, state):
            x, y, z = state
            return sigma * (y - x), x * (rho - z) - y, x * y - beta * z

        samples = Simulation(lorenz, (0.1, 0.0, 0.0)).solve(duration=18, step=0.015)
        points = [(x * 0.11, y * 0.11, (z - 24) * 0.11) for _, (x, y, z) in samples]
        attractor = Polyline(points, name="Lorenz Attractor", style=Style(color=(1.0, 0.3, 0.12, 1), width=0.012))
        self.play(Create(attractor), run_time=6)
        self.play(attractor.animate.rotate(0.8, axis="Z").scale(1.15), run_time=2)
        self.wait(0.5)
