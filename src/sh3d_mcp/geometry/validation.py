"""Validation helpers implementing the geometric rules from docs/VALIDATION.md."""

from __future__ import annotations

import math
from typing import Mapping

from sh3d_mcp.errors import ErrorCode, Sh3dError

from .primitives import (
    EPS_POINT,
    MIN_DIMENSION_LENGTH,
    MIN_ROOM_AREA,
    MIN_WALL_LENGTH,
    MIN_WALL_THICKNESS,
    Pt,
    dist,
    orient,
    oriented_rect_corners,
    point_in_polygon,
    polygon_bbox,
    sat_overlap,
    segments_collinear_overlap,
    segments_properly_intersect,
    shoelace_signed_area,
)


def check_scalars(**kwargs) -> None:
    """Validate numeric scalars and raise the documented error codes on failure."""

    _check_finite(kwargs)
    _check_coordinates(kwargs)

    thickness = kwargs.get("thickness")
    if thickness is not None and thickness <= MIN_WALL_THICKNESS:
        raise Sh3dError(
            ErrorCode.DEGENERATE_DIMENSION,
            f"Wall thickness must be > {MIN_WALL_THICKNESS} cm.",
            details={"thickness": thickness},
        )

    for name in ("height", "height_at_end"):
        value = kwargs.get(name)
        if value is not None and value <= 0:
            raise Sh3dError(
                ErrorCode.DEGENERATE_DIMENSION,
                f"{name} must be > 0.",
                details={name: value},
            )

    for name in ("width", "depth"):
        value = kwargs.get(name)
        if value is not None and value <= 0:
            raise Sh3dError(
                ErrorCode.DEGENERATE_DIMENSION,
                f"{name} must be > 0.",
                details={name: value},
            )

    elevation = kwargs.get("elevation")
    if elevation is not None and elevation < 0:
        raise Sh3dError(
            ErrorCode.DEGENERATE_DIMENSION,
            "elevation must be >= 0.",
            details={"elevation": elevation},
        )

    if "points" in kwargs:
        area = abs(shoelace_signed_area(kwargs["points"]))
        if area < MIN_ROOM_AREA:
            raise Sh3dError(
                ErrorCode.ROOM_DEGENERATE,
                f"Room area must be >= {MIN_ROOM_AREA} cm^2.",
                details={"area_cm2": area},
            )

    if all(name in kwargs for name in ("x1", "y1", "x2", "y2")):
        length = dist((kwargs["x1"], kwargs["y1"]), (kwargs["x2"], kwargs["y2"]))
        if any(name in kwargs for name in ("thickness", "height", "height_at_end")):
            if length < MIN_WALL_LENGTH:
                raise Sh3dError(
                    ErrorCode.WALL_TOO_SHORT,
                    f"Wall length must be >= {MIN_WALL_LENGTH} cm.",
                    details={"length": length},
                )
        elif "offset" in kwargs and length < MIN_DIMENSION_LENGTH:
            raise Sh3dError(
                ErrorCode.DEGENERATE_DIMENSION,
                f"Dimension line length must be >= {MIN_DIMENSION_LENGTH} cm.",
                details={"length": length},
            )

    if all(name in kwargs for name in ("width", "height", "wall_thickness")):
        if kwargs["width"] <= 2 * kwargs["wall_thickness"] or kwargs["height"] <= 2 * kwargs["wall_thickness"]:
            raise Sh3dError(
                ErrorCode.DEGENERATE_DIMENSION,
                "Project width and height must both be > 2 * wall_thickness.",
                details={
                    "width": kwargs["width"],
                    "height": kwargs["height"],
                    "wall_thickness": kwargs["wall_thickness"],
                },
            )


def validate_room_points(points: list[Pt]) -> tuple[list[Pt], list[str]]:
    """Normalize and validate a room polygon, returning cleaned points plus warnings."""

    warnings: list[str] = []
    cleaned = list(points)

    if len(cleaned) >= 4 and dist(cleaned[0], cleaned[-1]) <= EPS_POINT:
        cleaned = cleaned[:-1]
        warnings.append("Dropped a repeated closing point; room closure is implicit.")

    collapsed: list[Pt] = []
    for point in cleaned:
        if not collapsed or dist(collapsed[-1], point) > EPS_POINT:
            collapsed.append(point)
    cleaned = collapsed

    cleaned = _drop_collinear_points(cleaned)

    if len(cleaned) < 3:
        raise Sh3dError(
            ErrorCode.ROOM_TOO_FEW_POINTS,
            f"Room polygon has only {len(cleaned)} points; at least 3 are required.",
            details={"point_count": len(cleaned)},
            hint="Pass at least 3 distinct points; do not repeat the first point.",
        )

    area = abs(shoelace_signed_area(cleaned))
    if area < MIN_ROOM_AREA:
        raise Sh3dError(
            ErrorCode.ROOM_DEGENERATE,
            f"Room area {area} cm^2 is below the minimum {MIN_ROOM_AREA} cm^2.",
            details={"area_cm2": area},
        )

    _check_room_self_intersection(cleaned)

    if shoelace_signed_area(cleaned) < 0:
        cleaned.reverse()

    return cleaned, warnings


def rooms_overlap(points_a: list[Pt], points_b: list[Pt]) -> tuple[bool, dict | None]:
    """Return whether two room polygons overlap in their interiors."""

    bbox_a = polygon_bbox(points_a)
    bbox_b = polygon_bbox(points_b)
    if (
        bbox_a[2] < bbox_b[0] - EPS_POINT
        or bbox_b[2] < bbox_a[0] - EPS_POINT
        or bbox_a[3] < bbox_b[1] - EPS_POINT
        or bbox_b[3] < bbox_a[1] - EPS_POINT
    ):
        return False, None

    for i, (a1, a2) in enumerate(_polygon_edges(points_a)):
        for j, (b1, b2) in enumerate(_polygon_edges(points_b)):
            if segments_properly_intersect(a1, a2, b1, b2):
                return True, {"reason": "edge_crossing", "edges": [i, j]}

    for point in points_a:
        if point_in_polygon(point, points_b) == "inside":
            return True, {"reason": "a_inside_b", "point": point}
    for point in points_b:
        if point_in_polygon(point, points_a) == "inside":
            return True, {"reason": "b_inside_a", "point": point}

    return False, None


def wall_is_duplicate(start_a: Pt, end_a: Pt, start_b: Pt, end_b: Pt) -> tuple[bool, dict | None]:
    """Return whether two wall centrelines are collinear and overlap by more than a wall length."""

    if any(
        orient(p, q, r) != 0.0
        for p, q, r in ((start_a, end_a, start_b), (start_a, end_a, end_b))
    ):
        return False, None

    axis = 0 if abs(end_a[0] - start_a[0]) >= abs(end_a[1] - start_a[1]) else 1
    a_min, a_max = sorted((start_a[axis], end_a[axis]))
    b_min, b_max = sorted((start_b[axis], end_b[axis]))
    overlap = min(a_max, b_max) - max(a_min, b_min)
    if overlap > MIN_WALL_LENGTH:
        return True, {"overlap_length": overlap}
    return False, None


def walls_properly_cross(start_a: Pt, end_a: Pt, start_b: Pt, end_b: Pt) -> tuple[bool, dict | None]:
    """Return whether two wall centrelines form a strict X-junction crossing."""

    if segments_properly_intersect(start_a, end_a, start_b, end_b):
        return True, {"point_a": [start_a, end_a], "point_b": [start_b, end_b]}
    return False, None


def furniture_overlaps(
    piece_a: Mapping[str, float],
    piece_b: Mapping[str, float],
) -> tuple[bool, dict | None]:
    """Return whether two furniture footprints overlap, with elevation-disjoint note when relevant."""

    rect_a = oriented_rect_corners(
        piece_a["x"],
        piece_a["y"],
        piece_a["width"],
        piece_a["depth"],
        piece_a["angle"],
    )
    rect_b = oriented_rect_corners(
        piece_b["x"],
        piece_b["y"],
        piece_b["width"],
        piece_b["depth"],
        piece_b["angle"],
    )
    if not sat_overlap(rect_a, rect_b):
        return False, None

    details: dict[str, object] = {}
    if all(key in piece_a for key in ("elevation", "height")) and all(
        key in piece_b for key in ("elevation", "height")
    ):
        a_low = piece_a["elevation"]
        a_high = piece_a["elevation"] + piece_a["height"]
        b_low = piece_b["elevation"]
        b_high = piece_b["elevation"] + piece_b["height"]
        if a_high <= b_low or b_high <= a_low:
            details["note"] = "Elevation ranges are disjoint; pieces do not collide in 3D."

    return True, details


def _check_finite(values: object) -> None:
    """Recursively reject NaN and infinity values."""

    if values is None:
        return
    if isinstance(values, bool):
        return
    if isinstance(values, (int, float)):
        if not math.isfinite(values):
            raise Sh3dError(
                ErrorCode.INVALID_ARGUMENT,
                "Numeric arguments must be finite.",
                details={"value": values},
            )
        return
    if isinstance(values, Mapping):
        for value in values.values():
            _check_finite(value)
        return
    if isinstance(values, (list, tuple)):
        for value in values:
            _check_finite(value)


def _check_coordinates(kwargs: Mapping[str, object]) -> None:
    """Reject coordinates outside the documented +-1_000_000 cm bound."""

    coordinate_names = {
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "x_start",
        "y_start",
        "x_end",
        "y_end",
    }
    for name, value in kwargs.items():
        if name in coordinate_names and value is not None and abs(value) > 1_000_000:
            raise Sh3dError(
                ErrorCode.INVALID_ARGUMENT,
                "Coordinates must satisfy |v| <= 1_000_000.",
                details={name: value},
            )
        if name == "points" and value is not None:
            for x, y in value:
                if abs(x) > 1_000_000 or abs(y) > 1_000_000:
                    raise Sh3dError(
                        ErrorCode.INVALID_ARGUMENT,
                        "Coordinates must satisfy |v| <= 1_000_000.",
                        details={"point": (x, y)},
                    )


def _drop_collinear_points(points: list[Pt]) -> list[Pt]:
    """Remove collinear vertices when doing so preserves at least a triangle."""

    if len(points) < 4:
        return points

    cleaned = points
    changed = True
    while changed and len(cleaned) >= 4:
        changed = False
        candidate: list[Pt] = []
        for index, point in enumerate(cleaned):
            prev_point = cleaned[index - 1]
            next_point = cleaned[(index + 1) % len(cleaned)]
            if orient(prev_point, point, next_point) == 0.0:
                changed = True
                continue
            candidate.append(point)
        if len(candidate) >= 3:
            cleaned = candidate
        else:
            break
    return cleaned


def _check_room_self_intersection(points: list[Pt]) -> None:
    """Raise ROOM_SELF_INTERSECTS when a polygon is non-simple."""

    edges = _polygon_edges(points)
    for i, (a1, a2) in enumerate(edges):
        for j in range(i + 1, len(edges)):
            if j == i + 1 or (i == 0 and j == len(edges) - 1):
                continue
            b1, b2 = edges[j]
            if segments_properly_intersect(a1, a2, b1, b2) or segments_collinear_overlap(a1, a2, b1, b2):
                raise Sh3dError(
                    ErrorCode.ROOM_SELF_INTERSECTS,
                    "Room polygon is not simple.",
                    details={"edges": [i, j]},
                )
            shared = {a1, a2}.intersection({b1, b2})
            if shared:
                raise Sh3dError(
                    ErrorCode.ROOM_SELF_INTERSECTS,
                    "Room polygon touches itself at a non-adjacent vertex.",
                    details={"edges": [i, j]},
                )


def _polygon_edges(points: list[Pt]) -> list[tuple[Pt, Pt]]:
    """Return the closed edge list for a polygon."""

    return [(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]
