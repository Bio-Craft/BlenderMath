"""Coordinate systems, graph objects, and adaptive function sampling."""

from __future__ import annotations

import math
from collections.abc import Callable

from .expression import Expression, ExpressionError
from .colors import BLUE_C, WHITE
from .geometry import Line, Polyline
from .mobject import MObject, Style, VGroup
from .text import Text
from .vectors import add, vec3


def _range(value, default_step=1.0):
    if len(value) == 2:
        return float(value[0]), float(value[1]), float(default_step)
    if len(value) == 3:
        return tuple(float(item) for item in value)
    raise ValueError("Range must be (min, max) or (min, max, step)")


class FunctionGraph(VGroup):
    kind = "function_graph"

    def __init__(self, *curves: Polyline, function=None, domain=None, name="FunctionGraph"):
        super().__init__(*curves, name=name)
        self.function = function
        self.domain = domain


class BarChart(MObject):
    """A data-space bar chart compiled as one multi-stroke Grease Pencil object."""

    kind = "shape_2d_multi"

    def __init__(
        self,
        axes,
        values,
        *,
        x_values=None,
        widths=None,
        bar_width=None,
        baseline=0.0,
        gap_ratio=0.1,
        style=None,
        name="BarChart",
    ):
        super().__init__(name=name, style=style or Style(
            color=BLUE_C,
            width=0.006,
            fill_color=BLUE_C,
            fill_opacity=0.85,
        ))
        self.axes = axes
        self.values = tuple(float(value) for value in values)
        if not self.values:
            raise ValueError("BarChart requires at least one value")
        self.x_values = tuple(
            float(value) for value in
            (range(len(self.values)) if x_values is None else x_values)
        )
        if len(self.x_values) != len(self.values):
            raise ValueError("x_values and values must have equal lengths")
        if widths is not None and bar_width is not None:
            raise ValueError("Pass widths or bar_width, not both")
        if widths is None:
            if bar_width is None:
                if len(self.x_values) > 1:
                    bar_width = min(
                        abs(right - left)
                        for left, right in zip(self.x_values, self.x_values[1:])
                    )
                else:
                    bar_width = abs(float(axes.x_range[2]))
            widths = [bar_width] * len(self.values)
        self.widths = tuple(float(width) for width in widths)
        if len(self.widths) != len(self.values) or any(width <= 0 for width in self.widths):
            raise ValueError("widths must contain one positive value per bar")
        if not 0 <= gap_ratio < 1:
            raise ValueError("gap_ratio must be in [0, 1)")
        self.baseline = float(baseline)
        self.gap_ratio = float(gap_ratio)
        self.baseline_point = axes.c2p(self.x_values[0], self.baseline)
        self._update_geometry()

    def _update_geometry(self):
        strokes = []
        for x, value, width in zip(self.x_values, self.values, self.widths):
            half_width = width * (1 - self.gap_ratio) / 2
            left, right = x - half_width, x + half_width
            strokes.append([
                self.axes.c2p(left, self.baseline),
                self.axes.c2p(right, self.baseline),
                self.axes.c2p(right, value),
                self.axes.c2p(left, value),
            ])
        self.geometry.update({
            "strokes": strokes,
            "cyclic": True,
            "values": self.values,
            "x_values": self.x_values,
            "widths": self.widths,
            "baseline": self.baseline,
        })

    def set_values(self, values):
        values = tuple(float(value) for value in values)
        if len(values) != len(self.values):
            raise ValueError("New values must preserve the number of bars")
        self.values = values
        self._update_geometry()
        return self


class NumberLine(VGroup):
    kind = "number_line"

    def __init__(self, x_range=(-5, 5, 1), length: float = 10.0, include_ticks=True,
                 include_numbers=False, include_axis_label=True, axis_label="x",
                 label_type=Text, style=None, name="NumberLine"):
        self.x_range = _range(x_range)
        self.length = float(length)
        line_style = style or Style(color=WHITE, width=0.015)
        axis = Line((-length / 2, 0, 0), (length / 2, 0, 0), name="Axis", style=line_style)
        ticks = []
        if include_ticks:
            start, end, step = self.x_range
            value = math.ceil(start / step) * step
            while value <= end + step * 1e-9:
                x = self.n2p(value)[0]
                ticks.append(Line((x, 0, -0.07), (x, 0, 0.07), name=f"Tick {value:g}", style=line_style))
                value += step
        super().__init__(axis, *ticks, name=name)
        if include_numbers:
            self.add_numbers(label_type=label_type)
        if include_axis_label:
            self.add(_make_label(label_type, axis_label, .3, name="Number Line Axis Label", math=True).move_to((length / 2 + .3, 0, 0)))

    def n2p(self, number: float):
        start, end, _ = self.x_range
        return ((float(number) - start) / (end - start) - 0.5) * self.length, 0.0, 0.0

    def p2n(self, point):
        x = vec3(point)[0]
        start, end, _ = self.x_range
        return (x / self.length + 0.5) * (end - start) + start

    def add_numbers(self, values=None, *, font_size=0.24, exclude=(0,), label_type=Text):
        start, end, step = self.x_range
        values = values if values is not None else _values_in_range(start, end, step)
        labels = []
        for value in values:
            if any(abs(value - item) < 1e-10 for item in exclude):
                continue
            label = _make_label(
                label_type, f"{value:g}", font_size,
                name=f"Number {value:g}", math=True,
            )
            label.move_to(add(self.n2p(value), (0, 0, -0.24)))
            labels.append(label)
        group = VGroup(*labels, name="Number Labels")
        self.add(group)
        return group


class Axes(VGroup):
    kind = "axes"

    def __init__(
        self,
        x_range=(-5, 5, 1),
        y_range=(-3, 3, 1),
        x_length: float | None = None,
        y_length: float | None = None,
        unit_size: float = 1.0,
        include_ticks: bool = True,
        tips: bool = False,
        include_axis_labels: bool = True,
        axis_labels=("x", "y"),
        axis_label_type=Text,
        style: Style | None = None,
        name: str = "Axes",
    ):
        self.x_range = _range(x_range)
        self.y_range = _range(y_range)
        if unit_size <= 0:
            raise ValueError("unit_size must be positive")
        x_span = self.x_range[1] - self.x_range[0]
        y_span = self.y_range[1] - self.y_range[0]
        if x_length is None and y_length is None:
            x_length, y_length = x_span * unit_size, y_span * unit_size
        elif x_length is None:
            x_length = x_span * (float(y_length) / y_span)
        elif y_length is None:
            y_length = y_span * (float(x_length) / x_span)
        self.x_length = float(x_length)
        self.y_length = float(y_length)
        axis_style = style or Style(color=WHITE, width=0.015)
        xmin, xmax, _ = self.x_range
        ymin, ymax, _ = self.y_range
        objects = [
            Line(self._c2p_local(xmin, 0), self._c2p_local(xmax, 0), name="X Axis", style=axis_style),
            Line(self._c2p_local(0, ymin), self._c2p_local(0, ymax), name="Y Axis", style=axis_style),
        ]
        if include_ticks:
            objects.extend(self._ticks(axis_style))
        super().__init__(*objects, name=name)
        self.geometry["tips"] = tips
        if include_axis_labels:
            self.add_axis_labels(*axis_labels, label_type=axis_label_type)

    def _ticks(self, style):
        ticks = []
        for axis, values in (("x", self.x_range), ("y", self.y_range)):
            start, end, step = values
            value = math.ceil(start / step) * step
            while value <= end + step * 1e-9:
                if abs(value) > 1e-10:
                    point = self.c2p(value, 0) if axis == "x" else self.c2p(0, value)
                    delta = (0, 0, 0.065) if axis == "x" else (0.065, 0, 0)
                    ticks.append(Line(
                        (point[0] - delta[0], 0, point[2] - delta[2]),
                        (point[0] + delta[0], 0, point[2] + delta[2]),
                        name=f"{axis.upper()} Tick {value:g}", style=style,
                    ))
                value += step
        return ticks

    def c2p(self, x: float, y: float, z: float = 0.0):
        local = self._c2p_local(x, y, z)
        location = self.state.location if hasattr(self, "state") else (0.0, 0.0, 0.0)
        return add(local, location)

    def _c2p_local(self, x: float, y: float, z: float = 0.0):
        xmin, xmax, _ = self.x_range
        ymin, ymax, _ = self.y_range
        return (
            ((float(x) - xmin) / (xmax - xmin) - 0.5) * self.x_length,
            float(z),
            ((float(y) - ymin) / (ymax - ymin) - 0.5) * self.y_length,
        )

    coords_to_point = c2p

    def p2c(self, point):
        px, _py, pz = vec3(point)
        px -= self.state.location[0]
        pz -= self.state.location[2]
        xmin, xmax, _ = self.x_range
        ymin, ymax, _ = self.y_range
        return (
            (px / self.x_length + 0.5) * (xmax - xmin) + xmin,
            (pz / self.y_length + 0.5) * (ymax - ymin) + ymin,
        )

    point_to_coords = p2c

    def add_coordinates(
        self, x_values=None, y_values=None, *, font_size=0.22,
        exclude=(0,), label_type=Text,
    ):
        labels = []
        for axis, supplied, values in (("x", x_values, self.x_range), ("y", y_values, self.y_range)):
            start, end, step = values
            selected = supplied if supplied is not None else _values_in_range(start, end, step)
            for value in selected:
                if any(abs(value - item) < 1e-10 for item in exclude):
                    continue
                point = self._c2p_local(value, 0) if axis == "x" else self._c2p_local(0, value)
                offset = (0, 0, -0.23) if axis == "x" else (-0.25, 0, 0)
                label = _make_label(
                    label_type, f"{value:g}", font_size,
                    name=f"{axis.upper()} Label {value:g}", math=True,
                )
                label.move_to(add(point, offset))
                labels.append(label)
        group = VGroup(*labels, name="Coordinate Labels")
        group.style = Style(color=WHITE)
        self.add(group)
        return group

    def get_axis_labels(self, x_label="x", y_label="y", *, font_size=0.3, label_type=Text):
        xmax = self.x_range[1]
        ymax = self.y_range[1]
        x_end = self._c2p_local(xmax, 0)
        y_end = self._c2p_local(0, ymax)
        x = _make_label(label_type, x_label, font_size, name="X Axis Label", math=True).move_to(add(x_end, (0.3, 0, 0)))
        y = _make_label(label_type, y_label, font_size, name="Y Axis Label", math=True).move_to(add(y_end, (0, 0, 0.3)))
        labels = VGroup(x, y, name="Axis Labels")
        labels.style = Style(color=WHITE)
        return labels

    def add_axis_labels(self, *args, **kwargs):
        labels = self.get_axis_labels(*args, **kwargs)
        self.add(labels)
        return labels

    def get_bar_chart(self, values, **kwargs):
        """Create a filled 2D Grease Pencil bar chart in this axes' coordinates."""
        return BarChart(self, values, **kwargs)

    def get_riemann_rectangles(
        self,
        function: str | Callable[[float], float],
        x_range=None,
        *,
        dx=1.0,
        input_sample_type="center",
        baseline=0.0,
        gap_ratio=0.0,
        style=None,
        name="Riemann Rectangles",
    ):
        """Sample a function into a 2D GP bar chart over adjacent intervals."""
        dx = float(dx)
        if dx <= 0:
            raise ValueError("dx must be positive")
        if input_sample_type not in {"left", "center", "right"}:
            raise ValueError("input_sample_type must be left, center, or right")
        start, end = x_range or self.x_range[:2]
        start, end = float(start), float(end)
        if end <= start:
            raise ValueError("x_range must increase")
        evaluator = Expression(function) if isinstance(function, str) else function
        centers, widths, values = [], [], []
        left = start
        while left < end - 1e-12:
            right = min(end, left + dx)
            sample = {
                "left": left,
                "center": (left + right) / 2,
                "right": right,
            }[input_sample_type]
            try:
                value = evaluator(x=sample) if isinstance(evaluator, Expression) else evaluator(sample)
                value = float(value)
            except (ArithmeticError, ValueError, TypeError, ExpressionError) as error:
                raise ValueError(f"Function is not finite at x={sample:g}") from error
            if not math.isfinite(value):
                raise ValueError(f"Function is not finite at x={sample:g}")
            centers.append((left + right) / 2)
            widths.append(right - left)
            values.append(value)
            left = right
        return BarChart(
            self,
            values,
            x_values=centers,
            widths=widths,
            baseline=baseline,
            gap_ratio=gap_ratio,
            style=style,
            name=name,
        )

    def plot_parametric(
        self,
        function,
        domain=(0.0, math.tau),
        samples: int = 256,
        style: Style | None = None,
        name: str = "ParametricCurve",
    ) -> FunctionGraph:
        if samples < 2:
            raise ValueError("samples must be at least 2")
        start, end = domain
        points = []
        for index in range(samples):
            t = start + (end - start) * index / (samples - 1)
            coordinates = tuple(function(t))
            if len(coordinates) == 2:
                points.append(self.c2p(coordinates[0], coordinates[1]))
            elif len(coordinates) == 3:
                points.append(self.c2p(*coordinates))
            else:
                raise ValueError("Parametric function must return 2 or 3 coordinates")
        curve = Polyline(points, name=name, style=style or Style(color=(1.0, 0.35, 0.18, 1), width=0.025))
        return FunctionGraph(curve, function=function, domain=domain, name=name)

    def plot_polar(self, function, domain=(0.0, math.tau), **kwargs):
        return self.plot_parametric(
            lambda theta: (
                function(theta) * math.cos(theta),
                function(theta) * math.sin(theta),
            ),
            domain=domain,
            **kwargs,
        )

    def plot(
        self,
        function: str | Callable[[float], float],
        domain=None,
        samples: int = 64,
        adaptive: bool = True,
        tolerance: float = 0.015,
        max_depth: int = 9,
        style: Style | None = None,
        name: str = "FunctionGraph",
    ) -> FunctionGraph:
        xmin, xmax, _ = self.x_range
        start, end = domain or (xmin, xmax)
        evaluator = Expression(function) if isinstance(function, str) else function

        def evaluate(x):
            try:
                y = evaluator(x=x) if isinstance(evaluator, Expression) else evaluator(x)
                y = float(y)
                return y if math.isfinite(y) else None
            except (ArithmeticError, ValueError, TypeError, ExpressionError):
                return None

        raw = []
        step = (end - start) / max(1, samples - 1)

        def subdivide(x0, y0, x1, y1, depth):
            if not adaptive or depth >= max_depth or y0 is None or y1 is None:
                return [(x0, y0), (x1, y1)]
            mid = (x0 + x1) / 2
            ym = evaluate(mid)
            if ym is None:
                return [(x0, y0), (mid, None), (x1, y1)]
            linear_mid = (y0 + y1) / 2
            screen_error = abs(ym - linear_mid) * self.y_length / (self.y_range[1] - self.y_range[0])
            if screen_error <= tolerance:
                return [(x0, y0), (x1, y1)]
            return subdivide(x0, y0, mid, ym, depth + 1)[:-1] + subdivide(mid, ym, x1, y1, depth + 1)

        previous_x, previous_y = start, evaluate(start)
        raw.append((previous_x, previous_y))
        for index in range(1, samples):
            x = start + index * step
            y = evaluate(x)
            raw.extend(subdivide(previous_x, previous_y, x, y, 0)[1:])
            previous_x, previous_y = x, y

        segments, current = [], []
        yrange = self.y_range[1] - self.y_range[0]
        for (x, y), following in zip(raw, raw[1:] + [(None, None)]):
            discontinuity = y is None
            if y is not None and following[1] is not None:
                discontinuity |= abs(following[1] - y) > yrange * 2
            if not discontinuity:
                current.append(self.c2p(x, y))
            if discontinuity or following[0] is None:
                if len(current) >= 2:
                    segments.append(current)
                current = []
        graph_style = style or Style(color=(0.08, 0.55, 1.0, 1), width=0.025)
        curves = [Polyline(points, name=f"{name} {i + 1}", style=graph_style) for i, points in enumerate(segments)]
        if not curves:
            raise ValueError("Function produced no drawable segments")
        return FunctionGraph(*curves, function=function, domain=(start, end), name=name)


class NumberPlane(Axes):
    kind = "number_plane"

    def __init__(self, *args, background_line_style: Style | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        grid_style = background_line_style or Style(color=(0.28, 0.32, 0.38, 0.5), width=0.008)
        xmin, xmax, xstep = self.x_range
        ymin, ymax, ystep = self.y_range
        grid = []
        x = math.ceil(xmin / xstep) * xstep
        while x <= xmax + xstep * 1e-9:
            if abs(x) > 1e-10:
                grid.append(Line(self.c2p(x, ymin), self.c2p(x, ymax), style=grid_style, name="Grid X"))
            x += xstep
        y = math.ceil(ymin / ystep) * ystep
        while y <= ymax + ystep * 1e-9:
            if abs(y) > 1e-10:
                grid.append(Line(self.c2p(xmin, y), self.c2p(xmax, y), style=grid_style, name="Grid Y"))
            y += ystep
        # Background lines precede axes so Create reveals the plane naturally.
        existing = list(self.children)
        for child in existing:
            self.remove(child)
        self.add(*grid, *existing)


class ThreeDAxes(Axes):
    kind = "three_d_axes"

    def __init__(self, *args, z_range=(-3, 3, 1), z_length=None, **kwargs):
        self.z_range = _range(z_range)
        z_span = self.z_range[1] - self.z_range[0]
        unit_size = float(kwargs.get("unit_size", 1.0))
        self.z_length = float(z_length if z_length is not None else z_span * unit_size)
        super().__init__(*args, **kwargs)
        style = self.children[0].style
        objects = [Line((0, -self.z_length / 2, 0), (0, self.z_length / 2, 0), name="Z Axis", style=style)]
        start, end, step = self.z_range
        for value in _values_in_range(start, end, step):
            if abs(value) < 1e-10:
                continue
            point = self._c2p_local(0, 0, value)
            objects.append(Line((-.065, point[1], 0), (.065, point[1], 0), name=f"Z Tick {value:g}", style=style))
        self.add(*objects)

    def _c2p_local(self, x, y, z=0.0):
        px, _depth, pz = super()._c2p_local(x, y, 0)
        zmin, zmax, _ = self.z_range
        depth = ((float(z) - zmin) / (zmax - zmin) - 0.5) * self.z_length
        return px, depth, pz

    def p2c(self, point):
        px, py, pz = vec3(point)
        lx, ly, lz = self.state.location
        xmin, xmax, _ = self.x_range
        ymin, ymax, _ = self.y_range
        zmin, zmax, _ = self.z_range
        return (
            ((px - lx) / self.x_length + 0.5) * (xmax - xmin) + xmin,
            ((pz - lz) / self.y_length + 0.5) * (ymax - ymin) + ymin,
            ((py - ly) / self.z_length + 0.5) * (zmax - zmin) + zmin,
        )

    def get_axis_labels(self, x_label="x", y_label="y", z_label="z", *, font_size=0.3, label_type=Text):
        labels = super().get_axis_labels(x_label, y_label, font_size=font_size, label_type=label_type)
        z = _make_label(label_type, z_label, font_size, name="Z Axis Label", math=True).move_to((0, self.z_length / 2 + .3, 0))
        result = VGroup(*labels.children, z, name="3D Axis Labels")
        result.style = Style(color=WHITE)
        return result


def _values_in_range(start, end, step):
    values = []
    value = math.ceil(start / step) * step
    while value <= end + step * 1e-9:
        values.append(value)
        value += step
    return values


def _make_label(label_type, text, font_size, *, name, math=False):
    from .text import MathTex

    if isinstance(label_type, type) and issubclass(label_type, MathTex):
        source = f"$ {text} $" if math else text
        return label_type(source, name=name, style=Style(color=WHITE, fill_color=WHITE, fill_opacity=1.0)).scale(font_size / .7)
    return label_type(text, font_size=font_size, name=name, style=Style(color=WHITE))
