import math

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.validation import (
    check_scalars,
    furniture_overlaps,
    rooms_overlap,
    validate_room_points,
    wall_is_duplicate,
    walls_properly_cross,
)


def test_rule_2_check_scalars_rejects_non_finite_and_out_of_range_and_degenerate_values() -> None:
    with pytest.raises(Sh3dError) as exc_info:
        check_scalars(x=math.nan)
    assert exc_info.value.code is ErrorCode.INVALID_ARGUMENT

    with pytest.raises(Sh3dError) as exc_info:
        check_scalars(x=1_000_001)
    assert exc_info.value.code is ErrorCode.INVALID_ARGUMENT

    with pytest.raises(Sh3dError) as exc_info:
        check_scalars(thickness=0.1, x1=0.0, y1=0.0, x2=2.0, y2=0.0)
    assert exc_info.value.code is ErrorCode.DEGENERATE_DIMENSION

    with pytest.raises(Sh3dError) as exc_info:
        check_scalars(thickness=0.2, x1=0.0, y1=0.0, x2=0.0, y2=0.0)
    assert exc_info.value.code is ErrorCode.WALL_TOO_SHORT

    with pytest.raises(Sh3dError) as exc_info:
        check_scalars(offset=20.0, x1=0.0, y1=0.0, x2=0.0, y2=0.05)
    assert exc_info.value.code is ErrorCode.DEGENERATE_DIMENSION

    with pytest.raises(Sh3dError) as exc_info:
        check_scalars(width=10.0, height=10.0, wall_thickness=6.0)
    assert exc_info.value.code is ErrorCode.DEGENERATE_DIMENSION


def test_rule_4_1_validate_room_points_drops_repeated_closing_point_with_warning() -> None:
    points, warnings = validate_room_points(
        [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0), (0.0, 0.0)]
    )
    assert len(points) == 4
    assert warnings == ["Dropped a repeated closing point; room closure is implicit."]


def test_rule_4_2_validate_room_points_rejects_too_few_points_after_cleanup() -> None:
    with pytest.raises(Sh3dError) as exc_info:
        validate_room_points([(0.0, 0.0), (0.0, 0.0), (20.0, 0.0)])
    assert exc_info.value.code is ErrorCode.ROOM_TOO_FEW_POINTS


def test_rule_4_3_validate_room_points_rejects_room_below_minimum_area() -> None:
    with pytest.raises(Sh3dError) as exc_info:
        validate_room_points([(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)])
    assert exc_info.value.code is ErrorCode.ROOM_DEGENERATE


def test_rule_4_4_validate_room_points_rejects_self_intersection_and_pinch() -> None:
    with pytest.raises(Sh3dError) as exc_info:
        validate_room_points([(0.0, 0.0), (20.0, 0.0), (10.0, 10.0), (20.0, 20.0), (0.0, 20.0), (10.0, 10.0)])
    assert exc_info.value.code is ErrorCode.ROOM_SELF_INTERSECTS


def test_rule_4_5_validate_room_points_normalizes_winding_to_positive_area() -> None:
    points, warnings = validate_room_points([(0.0, 0.0), (0.0, 20.0), (20.0, 20.0), (20.0, 0.0)])
    assert warnings == []
    signed_area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        signed_area += (point[0] * next_point[1]) - (next_point[0] * point[1])
    assert signed_area / 2.0 > 0.0


def test_rule_4_6_rooms_overlap_detects_full_containment_but_not_shared_edge() -> None:
    overlap, details = rooms_overlap(
        [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)],
        [(5.0, 5.0), (10.0, 5.0), (10.0, 10.0), (5.0, 10.0)],
    )
    assert overlap is True
    assert details is not None

    overlap, details = rooms_overlap(
        [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        [(10.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0)],
    )
    assert overlap is False
    assert details is None


def test_rule_5_1_wall_is_duplicate_detects_collinear_overlap_longer_than_minimum() -> None:
    duplicate, details = wall_is_duplicate((0.0, 0.0), (5.0, 0.0), (2.0, 0.0), (8.0, 0.0))
    assert duplicate is True
    assert details == {"overlap_length": 3.0}

    duplicate, details = wall_is_duplicate((0.0, 0.0), (1.0, 0.0), (1.0, 0.0), (2.0, 0.0))
    assert duplicate is False
    assert details is None


def test_rule_5_2_walls_properly_cross_ignores_endpoint_touching() -> None:
    crossing, details = walls_properly_cross((0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0))
    assert crossing is True
    assert details is not None

    crossing, details = walls_properly_cross((0.0, 0.0), (1.0, 0.0), (1.0, 0.0), (1.0, 1.0))
    assert crossing is False
    assert details is None


def test_rule_6_furniture_overlaps_returns_overlap_and_elevation_note_when_disjoint_in_3d() -> None:
    overlap, details = furniture_overlaps(
        {"x": 0.0, "y": 0.0, "width": 4.0, "depth": 4.0, "angle": 0.0, "elevation": 0.0, "height": 1.0},
        {"x": 1.0, "y": 1.0, "width": 4.0, "depth": 4.0, "angle": 0.0, "elevation": 10.0, "height": 1.0},
    )
    assert overlap is True
    assert details == {"note": "Elevation ranges are disjoint; pieces do not collide in 3D."}

    overlap, details = furniture_overlaps(
        {"x": 0.0, "y": 0.0, "width": 4.0, "depth": 4.0, "angle": 0.0},
        {"x": 10.0, "y": 10.0, "width": 4.0, "depth": 4.0, "angle": 0.0},
    )
    assert overlap is False
    assert details is None
