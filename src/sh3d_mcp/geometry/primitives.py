"""Geometric primitives and tolerances for Sweet Home 3D plan validation."""

from __future__ import annotations

import math
from typing import Literal

Pt = tuple[float, float]
PointInPolygonResult = Literal["inside", "outside", "boundary"]

EPS_POINT = 1e-3
EPS_PARALLEL = 1e-9
JOIN_TOLERANCE = 2.0
MIN_WALL_LENGTH = 1.0
MIN_WALL_THICKNESS = 0.1
MIN_DIMENSION_LENGTH = 0.1
MIN_ROOM_AREA = 100.0
ROOM_OVERLAP_TOL = 1.0


def almost_equal(a: float, b: float, eps: float = EPS_POINT) -> bool:
    """Return whether two scalars are equal within the supplied tolerance."""

    return abs(a - b) <= eps


def dist(a: Pt, b: Pt) -> float:
    """Return the Euclidean distance between two points."""

    return math.hypot(b[0] - a[0], b[1] - a[1])


def orient(a: Pt, b: Pt, c: Pt) -> float:
    """Return the signed 2D cross product of AB and AC, zeroing near-parallel values."""

    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0.0 if abs(value) < EPS_PARALLEL else value


def segments_properly_intersect(a1: Pt, a2: Pt, b1: Pt, b2: Pt) -> bool:
    """Return True only for strict interior segment crossings, excluding touching endpoints."""

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)
    return (o1 * o2 < 0.0) and (o3 * o4 < 0.0)


def segments_collinear_overlap(a1: Pt, a2: Pt, b1: Pt, b2: Pt) -> bool:
    """Return True when collinear segments overlap by more than a single point."""

    if any(
        orient(p, q, r) != 0.0
        for p, q, r in ((a1, a2, b1), (a1, a2, b2), (b1, b2, a1), (b1, b2, a2))
    ):
        return False

    axis = 0 if abs(a2[0] - a1[0]) >= abs(a2[1] - a1[1]) else 1
    a_min, a_max = sorted((a1[axis], a2[axis]))
    b_min, b_max = sorted((b1[axis], b2[axis]))
    overlap = min(a_max, b_max) - max(a_min, b_min)
    return overlap > EPS_POINT


def shoelace_signed_area(points: list[Pt]) -> float:
    """Return the signed polygon area from the shoelace formula."""

    if len(points) < 3:
        return 0.0

    area2 = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area2 += (point[0] * next_point[1]) - (next_point[0] * point[1])
    return area2 / 2.0


def polygon_bbox(points: list[Pt]) -> tuple[float, float, float, float]:
    """Return a polygon bounding box as (min_x, min_y, max_x, max_y)."""

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def point_in_polygon(point: Pt, polygon: list[Pt]) -> PointInPolygonResult:
    """Return inside/outside/boundary using ray casting with explicit boundary detection."""

    px, py = point
    inside = False

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(point, start, end):
            return "boundary"

        x1, y1 = start
        x2, y2 = end
        crosses_scanline = (y1 > py) != (y2 > py)
        if not crosses_scanline:
            continue

        x_intersection = x1 + ((py - y1) * (x2 - x1) / (y2 - y1))
        if x_intersection > px:
            inside = not inside

    return "inside" if inside else "outside"


def oriented_rect_corners(x: float, y: float, w: float, d: float, angle_rad: float) -> list[Pt]:
    """Return the four corners of a centered oriented rectangle."""

    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    half_w = w / 2.0
    half_d = d / 2.0
    corners = []
    for sx, sy in [(-half_w, -half_d), (half_w, -half_d), (half_w, half_d), (-half_w, half_d)]:
        corners.append((x + (sx * cos_a) - (sy * sin_a), y + (sx * sin_a) + (sy * cos_a)))
    return corners


def sat_overlap(rect_a: list[Pt], rect_b: list[Pt]) -> bool:
    """Return True when two oriented rectangles overlap by area, excluding edge-only contact."""

    for axis in _sat_axes(rect_a) + _sat_axes(rect_b):
        min_a, max_a = _project_polygon(rect_a, axis)
        min_b, max_b = _project_polygon(rect_b, axis)
        if max_a <= min_b + EPS_POINT or max_b <= min_a + EPS_POINT:
            return False
    return True


def _point_on_segment(point: Pt, start: Pt, end: Pt) -> bool:
    """Return whether a point lies on a segment within tolerances."""

    if orient(start, end, point) != 0.0:
        return False

    px, py = point
    x1, y1 = start
    x2, y2 = end
    return (
        min(x1, x2) - EPS_POINT <= px <= max(x1, x2) + EPS_POINT
        and min(y1, y2) - EPS_POINT <= py <= max(y1, y2) + EPS_POINT
    )


def _sat_axes(rect: list[Pt]) -> list[Pt]:
    """Return the two unique edge normals needed for SAT on a rectangle."""

    axes = []
    for index in range(2):
        start = rect[index]
        end = rect[(index + 1) % len(rect)]
        edge_x = end[0] - start[0]
        edge_y = end[1] - start[1]
        normal = (-edge_y, edge_x)
        length = math.hypot(normal[0], normal[1])
        axes.append((normal[0] / length, normal[1] / length))
    return axes


def _project_polygon(points: list[Pt], axis: Pt) -> tuple[float, float]:
    """Project polygon points onto an axis and return min/max scalars."""

    projections = [(point[0] * axis[0]) + (point[1] * axis[1]) for point in points]
    return min(projections), max(projections)
