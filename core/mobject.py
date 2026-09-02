"""Manim-like scene graph objects with Blender-independent state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import itertools
import math
from typing import Any, Iterator

from .vectors import ORIGIN, Vec3, add, mul, vec3

Color = tuple[float, float, float, float]
_IDS = itertools.count(1)


@dataclass
class TransformState:
    location: Vec3 = ORIGIN
    rotation: Vec3 = ORIGIN
    scale: Vec3 = (1.0, 1.0, 1.0)
    opacity: float = 1.0
    draw_progress: float = 1.0
    visible: bool = True


@dataclass
class Style:
    color: Color = (0.08, 0.55, 1.0, 1.0)
    width: float = 0.025
    fill_color: Color | None = None
    fill_opacity: float = 0.0


class MObject:
    """A transformable node which may own geometry and child nodes."""

    kind = "group"

    def __init__(self, name: str | None = None, *, style: Style | None = None):
        self.uid = f"bm_{next(_IDS):06d}"
        self.name = name or type(self).__name__
        self.state = TransformState()
        self.style = style or Style()
        self.children: list[MObject] = []
        self.parent: MObject | None = None
        self.geometry: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}
        self.updaters: list[Any] = []

    def add(self, *mobjects: "MObject") -> "MObject":
        for child in mobjects:
            if child is self or self in child.family():
                raise ValueError("MObject hierarchy cannot contain cycles")
            if child.parent is not None:
                child.parent.remove(child)
            child.parent = self
            self.children.append(child)
        return self

    def remove(self, *mobjects: "MObject") -> "MObject":
        for child in mobjects:
            if child in self.children:
                self.children.remove(child)
                child.parent = None
        return self

    def family(self) -> Iterator["MObject"]:
        yield self
        for child in self.children:
            yield from child.family()

    def copy(self) -> "MObject":
        result = deepcopy(self)
        for node in result.family():
            node.uid = f"bm_{next(_IDS):06d}"
        return result

    def move_to(self, point) -> "MObject":
        target = vec3(point)
        center = self.get_center()
        return self._shift_world(tuple(a - b for a, b in zip(target, center)))

    def shift(self, vector) -> "MObject":
        return self._shift_world(vector)

    def scale(self, factor: float | tuple[float, float, float], about_point=None) -> "MObject":
        if isinstance(factor, (int, float)):
            factor = (float(factor),) * 3
        factor = vec3(factor)
        anchor = self.get_center() if about_point is None else vec3(about_point)
        anchor_local = self._point_from_world(anchor)
        self.state.scale = tuple(a * b for a, b in zip(self.state.scale, factor))  # type: ignore[assignment]
        moved_anchor = self._point_to_world(anchor_local)
        self._shift_world(tuple(a - b for a, b in zip(anchor, moved_anchor)))
        return self

    def scale_x(self, factor: float, about_point=None) -> "MObject":
        return self.scale((factor, 1.0, 1.0), about_point=about_point)

    def scale_y(self, factor: float, about_point=None) -> "MObject":
        return self.scale((1.0, 1.0, factor), about_point=about_point)

    def rotate(self, angle: float, axis: str = "Y", about_point=None) -> "MObject":
        indexes = {"X": 0, "Y": 1, "Z": 2}
        if axis.upper() not in indexes:
            raise ValueError("axis must be X, Y, or Z")
        anchor = self.get_center() if about_point is None else vec3(about_point)
        anchor_local = self._point_from_world(anchor)
        values = list(self.state.rotation)
        values[indexes[axis.upper()]] += float(angle)
        self.state.rotation = tuple(values)  # type: ignore[assignment]
        moved_anchor = self._point_to_world(anchor_local)
        self._shift_world(tuple(a - b for a, b in zip(anchor, moved_anchor)))
        return self

    def set_opacity(self, opacity: float) -> "MObject":
        self.state.opacity = max(0.0, min(1.0, float(opacity)))
        return self

    def set_color(self, color: Color) -> "MObject":
        color = tuple(float(item) for item in color)
        self.style.color = color  # type: ignore[assignment]
        self.style.fill_color = color  # type: ignore[assignment]
        return self

    def set_stroke(self, color: Color | None = None, width: float | None = None) -> "MObject":
        if color is not None:
            self.style.color = tuple(float(item) for item in color)  # type: ignore[assignment]
        if width is not None:
            self.style.width = float(width)
        return self

    def set_fill(self, color: Color | None = None, opacity: float | None = None) -> "MObject":
        if color is not None:
            self.style.fill_color = tuple(float(item) for item in color)  # type: ignore[assignment]
        if opacity is not None:
            self.style.fill_opacity = max(0.0, min(1.0, float(opacity)))
        return self

    def next_to(self, other: "MObject", direction=(1, 0, 0), buff: float = 0.25) -> "MObject":
        unit = _normalize(vec3(direction))
        own_center = self.get_center()
        other_center = other.get_center()
        own_extent = self._extent_along(unit)
        other_extent = other._extent_along(unit)
        destination = add(other_center, mul(unit, other_extent + own_extent + float(buff)))
        self.shift(tuple(a - b for a, b in zip(destination, own_center)))
        return self

    def get_bounding_box(self):
        points = []
        for node in self.family():
            for point in node._local_bounding_points():
                points.append(node._point_to_world(point))
        if not points:
            center = self._point_to_world(ORIGIN)
            return center, center
        return (
            tuple(min(point[index] for point in points) for index in range(3)),
            tuple(max(point[index] for point in points) for index in range(3)),
        )

    def _local_bounding_points(self):
        points = self.geometry.get("points")
        if points:
            return list(points)
        strokes = self.geometry.get("strokes")
        if strokes:
            return [point for stroke in strokes for point in stroke]
        if self.kind == "text":
            size = float(self.geometry.get("font_size", 0.28))
            width = max(size * .5, size * .62 * len(self.geometry.get("text", "")))
            return _box_points(width, 0.0, size)
        if self.kind == "math":
            layout_width = self.geometry.get("layout_width")
            layout_height = self.geometry.get("layout_height")
            if layout_width is not None and layout_height is not None:
                return _box_points(float(layout_width), 0.0, float(layout_height))
            visible = [token for token in getattr(self, "tokens", ()) if token.source not in {"^", "_", "{", "}"}]
            width = max(.4, len(visible) * .32)
            return _box_points(width, 0.0, .7)
        return []

    def _point_to_world(self, point):
        result = vec3(point)
        node = self
        while node is not None:
            result = _transform_point(result, node.state)
            node = node.parent
        return result

    def _point_from_world(self, point):
        result = vec3(point)
        chain = []
        node = self
        while node is not None:
            chain.append(node)
            node = node.parent
        for node in reversed(chain):
            result = tuple(a - b for a, b in zip(result, node.state.location))
            result = _inverse_rotate(result, node.state.rotation)
            if any(abs(value) < 1e-12 for value in node.state.scale):
                raise ValueError("Cannot transform through a zero scale")
            result = tuple(value / scale for value, scale in zip(result, node.state.scale))
        return result

    def _shift_world(self, vector):
        result = vec3(vector)
        ancestors = []
        node = self.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent
        for node in reversed(ancestors):
            result = _inverse_rotate(result, node.state.rotation)
            if any(abs(value) < 1e-12 for value in node.state.scale):
                raise ValueError("Cannot shift through a zero-scaled parent")
            result = tuple(value / scale for value, scale in zip(result, node.state.scale))
        self.state.location = add(self.state.location, result)
        return self

    def get_center(self):
        minimum, maximum = self.get_bounding_box()
        return tuple((left + right) / 2 for left, right in zip(minimum, maximum))

    def get_width(self):
        minimum, maximum = self.get_bounding_box()
        return maximum[0] - minimum[0]

    def get_height(self):
        minimum, maximum = self.get_bounding_box()
        return maximum[2] - minimum[2]

    def get_depth(self):
        minimum, maximum = self.get_bounding_box()
        return maximum[1] - minimum[1]

    def _extent_along(self, direction):
        minimum, maximum = self.get_bounding_box()
        half = tuple((right - left) / 2 for left, right in zip(minimum, maximum))
        return sum(abs(component) * extent for component, extent in zip(direction, half))

    def align_to(self, other: "MObject", direction=(1, 0, 0)) -> "MObject":
        direction = vec3(direction)
        own_min, own_max = self.get_bounding_box()
        other_min, other_max = other.get_bounding_box()
        shift = [0.0, 0.0, 0.0]
        for index, component in enumerate(direction):
            if component > 0:
                shift[index] = other_max[index] - own_max[index]
            elif component < 0:
                shift[index] = other_min[index] - own_min[index]
        return self.shift(tuple(shift))

    def to_edge(self, direction=(1, 0, 0), buff=.5, *, frame_width=14.222, frame_height=8.0):
        direction = _normalize(vec3(direction))
        minimum, maximum = self.get_bounding_box()
        shift = [0.0, 0.0, 0.0]
        if direction[0] > 0:
            shift[0] = frame_width / 2 - buff - maximum[0]
        elif direction[0] < 0:
            shift[0] = -frame_width / 2 + buff - minimum[0]
        if direction[2] > 0:
            shift[2] = frame_height / 2 - buff - maximum[2]
        elif direction[2] < 0:
            shift[2] = -frame_height / 2 + buff - minimum[2]
        return self.shift(tuple(shift))

    def to_corner(self, direction=(1, 0, 1), buff=.5, **kwargs):
        return self.to_edge(direction, buff, **kwargs)

    def match_width(self, other: "MObject"):
        width = self.get_width()
        return self.scale_x(other.get_width() / width) if width > 1e-12 else self

    def match_height(self, other: "MObject"):
        height = self.get_height()
        return self.scale_y(other.get_height() / height) if height > 1e-12 else self

    def add_updater(self, updater) -> "MObject":
        self.updaters.append(updater)
        return self

    @property
    def animate(self):
        from .animation import AnimationBuilder
        return AnimationBuilder(self)

    def __getitem__(self, index):
        return self.children[index]

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)


class VGroup(MObject):
    def __init__(self, *mobjects: MObject, name: str | None = None):
        super().__init__(name)
        self.add(*mobjects)

    def arrange(self, direction=(1, 0, 0), buff: float = 0.5, *, center=True, aligned_edge=None) -> "VGroup":
        if not self.children:
            return self
        original_center = self.get_center()
        for previous, child in zip(self.children, self.children[1:]):
            child.next_to(previous, direction, buff)
            if aligned_edge is not None:
                child.align_to(previous, aligned_edge)
        if center:
            center_after = self.get_center()
            delta = tuple(a - b for a, b in zip(original_center, center_after))
            for child in self.children:
                child.shift(delta)
        return self

    def arrange_in_grid(self, rows=None, cols=None, buff=(.5, .5), *, center=True):
        count = len(self.children)
        if count == 0:
            return self
        if rows is None and cols is None:
            cols = math.ceil(math.sqrt(count))
        if cols is None:
            cols = math.ceil(count / rows)
        if rows is None:
            rows = math.ceil(count / cols)
        if rows * cols < count:
            raise ValueError("rows * cols must fit all children")
        x_buff, z_buff = (float(buff), float(buff)) if isinstance(buff, (int, float)) else buff
        original_center = self.get_center()
        column_widths = [0.0] * cols
        row_heights = [0.0] * rows
        for index, child in enumerate(self.children):
            row, column = divmod(index, cols)
            column_widths[column] = max(column_widths[column], child.get_width())
            row_heights[row] = max(row_heights[row], child.get_height())
        xs = [0.0]
        for index in range(1, cols):
            xs.append(xs[-1] + column_widths[index - 1] / 2 + x_buff + column_widths[index] / 2)
        zs = [0.0]
        for index in range(1, rows):
            zs.append(zs[-1] - row_heights[index - 1] / 2 - z_buff - row_heights[index] / 2)
        for index, child in enumerate(self.children):
            row, column = divmod(index, cols)
            center_now = child.get_center()
            child.shift((xs[column] - center_now[0], 0, zs[row] - center_now[2]))
        if center:
            center_after = self.get_center()
            delta = tuple(a - b for a, b in zip(original_center, center_after))
            for child in self.children:
                child.shift(delta)
        return self


def _normalize(value):
    magnitude = math.sqrt(sum(component * component for component in value))
    if magnitude <= 1e-12:
        raise ValueError("Direction cannot be zero")
    return tuple(component / magnitude for component in value)


def _rotate(point, rotation):
    x, y, z = point
    rx, ry, rz = rotation
    cy, sy = math.cos(rx), math.sin(rx)
    y, z = y * cy - z * sy, y * sy + z * cy
    cy, sy = math.cos(ry), math.sin(ry)
    x, z = x * cy + z * sy, -x * sy + z * cy
    cy, sy = math.cos(rz), math.sin(rz)
    x, y = x * cy - y * sy, x * sy + y * cy
    return x, y, z


def _inverse_rotate(point, rotation):
    x, y, z = point
    rx, ry, rz = rotation
    cosine, sine = math.cos(rz), math.sin(rz)
    x, y = x * cosine + y * sine, -x * sine + y * cosine
    cosine, sine = math.cos(ry), math.sin(ry)
    x, z = x * cosine - z * sine, x * sine + z * cosine
    cosine, sine = math.cos(rx), math.sin(rx)
    y, z = y * cosine + z * sine, -y * sine + z * cosine
    return x, y, z


def _transform_point(point, state):
    scaled = tuple(value * factor for value, factor in zip(point, state.scale))
    return add(_rotate(scaled, state.rotation), state.location)


def _box_points(width, depth, height):
    return [
        (x, y, z)
        for x in (-width / 2, width / 2)
        for y in (-depth / 2, depth / 2)
        for z in (-height / 2, height / 2)
    ]
