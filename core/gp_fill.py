"""Fill grouping for compound vector outlines."""

from __future__ import annotations


def _bounds(polygon):
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _area(polygon):
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1])
        )
    ) * 0.5


def _point_inside(point, polygon):
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        on_edge = (
            abs(cross) <= 1e-9
            and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9
            and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9
        )
        if on_edge:
            return True
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
    return inside


def _contains(outer, inner):
    left, bottom, right, top = _bounds(outer)
    inner_left, inner_bottom, inner_right, inner_top = _bounds(inner)
    if not (
        left <= inner_left
        and bottom <= inner_bottom
        and right >= inner_right
        and top >= inner_top
    ):
        return False
    probes = inner + [
        ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
        for (x1, y1), (x2, y2) in zip(inner, inner[1:] + inner[:1])
    ]
    return all(_point_inside(point, outer) for point in probes)


def nested_fill_groups(polygons):
    """Group each outer contour with its nested holes.

    Grease Pencil treats every contour sharing a fill id as one even-odd
    region. Typst CJK glyphs often contain overlapping stroke outlines, so a
    single id cuts false holes at intersections. Separate top-level contours
    while retaining their nested hole contours in the same group.
    """
    polygons = [[tuple(point[:2]) for point in polygon] for polygon in polygons]
    areas = [_area(polygon) for polygon in polygons]
    parents = [None] * len(polygons)
    for child, polygon in enumerate(polygons):
        candidates = [
            index
            for index, outer in enumerate(polygons)
            if areas[index] > areas[child] and _contains(outer, polygon)
        ]
        if candidates:
            parents[child] = min(candidates, key=areas.__getitem__)

    roots = []
    groups = []
    for index in range(len(polygons)):
        root = index
        while parents[root] is not None:
            root = parents[root]
        if root not in roots:
            roots.append(root)
        groups.append(roots.index(root) + 1)
    return groups
