"""A binomial histogram growing from the axis, followed by its normal approximation."""

from math import comb, exp, pi, sqrt

from bmath import Axes, BLUE_C, Create, FadeIn, MathTex, RED_C, Scene, Style


class ProbabilityDistributionExample(Scene):
    def construct(self):
        n = 10
        p = 0.5
        axes = Axes(
            x_range=(-0.75, 10.75, 1),
            y_range=(0, 0.30, 0.05),
            x_length=9.2,
            y_length=4.8,
            include_axis_labels=False,
            style=Style(color=(1, 1, 1, 1), width=0.009),
            name="Probability Axes",
        )
        axes.add_coordinates(
            x_values=range(n + 1),
            y_values=(0.05, 0.10, 0.15, 0.20, 0.25, 0.30),
            exclude=(),
            font_size=0.17,
            label_type=MathTex,
        )
        axes.add_axis_labels(
            "k", "P(X = k)", font_size=0.25, label_type=MathTex,
        )

        self.play(Create(axes), run_time=1.6)

        probabilities = []
        label_animations = []
        bar_style = Style(
            color=BLUE_C,
            width=0.006,
            fill_color=BLUE_C,
            fill_opacity=0.92,
        )

        for k in range(n + 1):
            probability = comb(n, k) * p**k * (1 - p) ** (n - k)
            probabilities.append(probability)
            base = axes.c2p(k, 0)
            top = axes.c2p(k, probability)
            probability_label = MathTex(
                f"$ {probability:.3f} $",
                stroke_mode="NONE",
                name=f"Probability Label {k}",
            ).move_to(base).scale(0.001)

            label_animations.append(
                probability_label.animate(run_time=2.0)
                .move_to((top[0], top[1], top[2] + 0.15))
                .scale(200)
            )

        bars = axes.get_bar_chart(
            probabilities,
            x_values=range(n + 1),
            bar_width=0.72,
            gap_ratio=0,
            style=bar_style,
            name="Binomial Bars",
        )
        bars.scale_y(0.001, about_point=bars.baseline_point).set_opacity(0)
        self.play(
            bars.animate(run_time=2.0)
            .scale_y(1000, about_point=bars.baseline_point)
            .set_opacity(1),
            *label_animations,
            run_time=2.0,
        )
        self.wait(0.25)

        mean = n * p
        standard_deviation = sqrt(n * p * (1 - p))
        normal_curve = axes.plot(
            lambda x: exp(-0.5 * ((x - mean) / standard_deviation) ** 2)
            / (standard_deviation * sqrt(2 * pi)),
            domain=(-0.5, 10.5),
            samples=96,
            style=Style(color=RED_C, width=0.014),
            name="Normal Approximation",
        )
        self.play(Create(normal_curve), FadeIn(normal_curve), run_time=2.0)
        self.wait(1.0)
