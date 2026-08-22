"""Primitive mathematical geometry objects."""

from __future__ import annotations

import math

from .mobject import MObject, Style
from .colors import WHITE
from .vectors import ORIGIN, Vec3, add, vec3


class Polyline(MObject):
    kind = "shape_2d"

    def __init__(self, points, name: str | None = None, *, style: Style | None = None, cyclic: bool = False):
        super().__init__(name, style=style)
        values = [vec3(point) for point in points]
        if len(values) < 2:
            raise ValueError("Polyline needs at least two points")
        self.geometry.update(points=values, cyclic=bool(cyclic))

    @property
    def points(self) -> list[Vec3]:
        return self.geometry["points"]


class Line(Polyline):
    def __init__(self, start=(-1, 0, 0), end=(1, 0, 0), **kwargs):
        super().__init__([start, end], **kwargs)

    @property
    def start(self):
        return self.points[0]

    @property
    def end(self):
        return self.points[-1]


class Arrow(Line):
    kind = "shape_2d"

    def __init__(self, start=ORIGIN, end=(1, 0, 0), tip_length: float = 0.18, **kwargs):
        super().__init__(start, end, **kwargs)
        self.geometry["tip_length"] = float(tip_length)
        sx, sy, sz = self.start
        ex, ey, ez = self.end
        dx, dz = ex - sx, ez - sz
        magnitude = math.hypot(dx, dz)
        if magnitude == 0:
            raise ValueError("Arrow start and end must differ")
        ux, uz = dx / magnitude, dz / magnitude
        px, pz = -uz, ux
        base_x, base_z = ex - ux * tip_length, ez - uz * tip_length
        wing = tip_length * 0.55
        tip = Polyline(
            [(base_x + px * wing, ey, base_z + pz * wing), (ex, ey, ez), (base_x - px * wing, ey, base_z - pz * wing)],
            name=f"{self.name} Tip",
            style=self.style,
        )
        self.add(tip)


class Arrow3D(MObject):
    """Endpoint-driven 3D arrow compiled as a reusable Geometry Nodes asset."""

    kind = "geometry_nodes_arrow"

    def __init__(
        self, start=ORIGIN, end=(1, 0, 0), *, shaft_radius=.018,
        tip_radius=.065, tip_length=.16, style=None, name="Arrow3D",
    ):
        super().__init__(name, style=style)
        start, end = vec3(start), vec3(end)
        if start == end:
            raise ValueError("Arrow3D start and end must differ")
        self.geometry.update(
            start=start, end=end, shaft_radius=float(shaft_radius),
            tip_radius=float(tip_radius), tip_length=float(tip_length),
        )

    @property
    def start(self):
        return self.geometry["start"]

    @property
    def end(self):
        return self.geometry["end"]

    def put_start_and_end_on(self, start, end):
        start, end = vec3(start), vec3(end)
        if start == end:
            raise ValueError("Arrow3D start and end must differ")
        self.geometry["start"] = start
        self.geometry["end"] = end
        return self


class ThreeDAxes3D(MObject):
    kind = "three_d_axes_gn"

    def __init__(
        self, x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-3, 3, 1),
        x_length=None, y_length=None, z_length=None, unit_size=1.0,
        include_ticks=True, include_axis_labels=True, *, name="ThreeDAxes3D",
    ):
        from .colors import BLUE_C, GREEN_C, RED_C

        super().__init__(name)
        self.x_range = self._range(x_range)
        self.y_range = self._range(y_range)
        self.z_range = self._range(z_range)
        self.x_length = float(x_length or (self.x_range[1] - self.x_range[0]) * unit_size)
        self.y_length = float(y_length or (self.y_range[1] - self.y_range[0]) * unit_size)
        self.z_length = float(z_length or (self.z_range[1] - self.z_range[0]) * unit_size)
        self.add(
            Arrow3D(self.c2p(self.x_range[0], 0, 0), self.c2p(self.x_range[1], 0, 0), shaft_radius=.012, tip_radius=.045, tip_length=.13, style=Style(color=RED_C), name="X Axis 3D GN"),
            Arrow3D(self.c2p(0, self.y_range[0], 0), self.c2p(0, self.y_range[1], 0), shaft_radius=.012, tip_radius=.045, tip_length=.13, style=Style(color=GREEN_C), name="Y Axis 3D GN"),
            Arrow3D(self.c2p(0, 0, self.z_range[0]), self.c2p(0, 0, self.z_range[1]), shaft_radius=.012, tip_radius=.045, tip_length=.13, style=Style(color=BLUE_C), name="Z Axis 3D GN"),
        )
        if include_ticks:
            self.add(*self._ticks())
        if include_axis_labels:
            self.add_axis_labels()

    @staticmethod
    def _range(value):
        if len(value) == 2:
            value = (*value, 1)
        if len(value) != 3 or value[2] <= 0 or value[1] <= value[0]:
            raise ValueError("Axis range must be increasing (min, max, positive step)")
        return tuple(float(item) for item in value)

    @staticmethod
    def _values(values):
        start, end, step = values
        value = math.ceil(start / step) * step
        while value <= end + step * 1e-9:
            if abs(value) > 1e-10:
                yield value
            value += step

    def c2p(self, x, y, z=0.0):
        def map_value(value, values, length):
            start, end, _ = values
            return ((float(value) - start) / (end - start) - .5) * length
        return (
            map_value(x, self.x_range, self.x_length),
            map_value(z, self.z_range, self.z_length),
            map_value(y, self.y_range, self.y_length),
        )

    def _tick(self, start, end, name):
        return Arrow3D(
            start, end, shaft_radius=.005, tip_radius=.005, tip_length=.001,
            style=Style(color=WHITE), name=name,
        )

    def _ticks(self):
        ticks = []
        for value in self._values(self.x_range):
            x, y, z = self.c2p(value, 0, 0)
            ticks.append(self._tick((x, y, z - .08), (x, y, z + .08), f"X Tick {value:g}"))
        for value in self._values(self.y_range):
            x, y, z = self.c2p(0, value, 0)
            ticks.append(self._tick((x - .08, y, z), (x + .08, y, z), f"Y Tick {value:g}"))
        for value in self._values(self.z_range):
            x, y, z = self.c2p(0, 0, value)
            ticks.append(self._tick((x - .08, y, z), (x + .08, y, z), f"Z Tick {value:g}"))
        return ticks

    def add_axis_labels(self, x_label="x", y_label="y", z_label="z", font_size=.3):
        from .text import Text
        labels = MObject("3D Axis Labels")
        labels.add(
            Text(x_label, font_size=font_size, style=Style(color=WHITE)).move_to(add(self.c2p(self.x_range[1], 0, 0), (.3, 0, 0))),
            Text(y_label, font_size=font_size, style=Style(color=WHITE)).move_to(add(self.c2p(0, self.y_range[1], 0), (0, 0, .3))),
            Text(z_label, font_size=font_size, style=Style(color=WHITE)).move_to(add(self.c2p(0, 0, self.z_range[1]), (0, .3, 0))),
        )
        self.add(labels)
        return labels


class Circle(Polyline):
    kind = "shape_2d"
    def __init__(self, radius: float = 1.0, samples: int = 96, **kwargs):
        points = [
            (radius * math.cos(math.tau * i / samples), 0, radius * math.sin(math.tau * i / samples))
            for i in range(samples)
        ]
        super().__init__(points, cyclic=True, **kwargs)
        self.geometry["radius"] = float(radius)


class Rectangle(Polyline):
    kind = "shape_2d"
    def __init__(self, width: float = 2.0, height: float = 1.0, **kwargs):
        x, z = width / 2, height / 2
        super().__init__([(-x, 0, -z), (x, 0, -z), (x, 0, z), (-x, 0, z)], cyclic=True, **kwargs)
        self.geometry.update(width=float(width), height=float(height))


class Dot(MObject):
    kind = "shape_2d"

    def __init__(self, point=ORIGIN, radius: float = 0.07, *, representation="GREASE_PENCIL", samples=32, **kwargs):
        representation = representation.upper()
        if representation not in {"GREASE_PENCIL", "MESH"}:
            raise ValueError("Dot representation must be GREASE_PENCIL or MESH")
        style = kwargs.pop("style", None) or Style(
            color=WHITE, width=max(0.01, radius * .18), fill_color=WHITE, fill_opacity=1.0,
        )
        super().__init__(kwargs.pop("name", None), style=style)
        self.kind = "shape_2d" if representation == "GREASE_PENCIL" else "dot"
        self.representation = representation
        self.move_to(point)
        self.geometry.update(
            radius=float(radius),
            cyclic=True,
            points=[
                (radius * math.cos(math.tau * index / samples), 0, radius * math.sin(math.tau * index / samples))
                for index in range(samples)
            ],
        )
