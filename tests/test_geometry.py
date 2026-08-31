import math

import pytest

from sh3d_mcp.geometry.primitives import (
    EPS_PARALLEL,
    EPS_POINT,
    JOIN_TOLERANCE,
    MIN_DIMENSION_LENGTH,
    MIN_ROOM_AREA,
    MIN_WALL_LENGTH,
    MIN_WALL_THICKNESS,
    ROOM_OVERLAP_TOL,
    almost_equal,
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


def test_tolerance_constants_match_documented_values() -> None:
    assert EPS_POINT == 1e-3
    assert EPS_PARALLEL == 1e-9
    assert JOIN_TOLERANCE == 2.0
    assert MIN_WALL_LENGTH == 1.0
    assert MIN_WALL_THICKNESS == 0.1
    assert MIN_DIMENSION_LENGTH == 0.1
    assert MIN_ROOM_AREA == 100.0
    assert ROOM_OVERLAP_TOL == 1.0


@pytest.mark.parametrize(
    ("a", "b", "eps", "expected"),
    [
        (1.0, 1.0 + (EPS_POINT / 2.0), EPS_POINT, True),
        (1.0, 1.0 + (EPS_POINT * 2.0), EPS_POINT, False),
    ],
)
def test_almost_equal(a: float, b: float, eps: float, expected: bool) -> None:
    assert almost_equal(a, b, eps) is expected


def test_dist() -> None:
    assert dist((0.0, 0.0), (3.0, 4.0)) == 5.0


def test_orient_zeroes_near_parallel_values() -> None:
    assert orient((0.0, 0.0), (1.0, 0.0), (2.0, EPS_PARALLEL / 2.0)) == 0.0
    assert orient((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)) > 0.0
    assert orient((0.0, 0.0), (1.0, 0.0), (1.0, -1.0)) < 0.0


@pytest.mark.parametrize(
    ("a1", "a2", "b1", "b2", "expected"),
    [
        ((0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0), True),
        ((0.0, 0.0), (1.0, 0.0), (1.0, 0.0), (1.0, 1.0), False),
        ((0.0, 0.0), (2.0, 0.0), (1.0, 0.0), (3.0, 0.0), False),
    ],
)
def test_segments_properly_intersect(a1, a2, b1, b2, expected: bool) -> None:
    assert segments_properly_intersect(a1, a2, b1, b2) is expected


@pytest.mark.parametrize(
    ("a1", "a2", "b1", "b2", "expected"),
    [
        ((0.0, 0.0), (4.0, 0.0), (2.0, 0.0), (6.0, 0.0), True),
        ((0.0, 0.0), (4.0, 0.0), (4.0, 0.0), (6.0, 0.0), False),
        ((0.0, 0.0), (4.0, 0.0), (5.0, 0.0), (6.0, 0.0), False),
        ((0.0, 0.0), (4.0, 0.0), (2.0, 1.0), (6.0, 1.0), False),
    ],
)
def test_segments_collinear_overlap(a1, a2, b1, b2, expected: bool) -> None:
    assert segments_collinear_overlap(a1, a2, b1, b2) is expected


def test_shoelace_signed_area() -> None:
    assert shoelace_signed_area([(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)]) == 12.0


def test_polygon_bbox() -> None:
    assert polygon_bbox([(2.0, 5.0), (-1.0, 3.0), (4.0, -2.0)]) == (-1.0, -2.0, 4.0, 5.0)


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((2.0, 2.0), "inside"),
        ((5.0, 2.0), "boundary"),
        ((6.0, 2.0), "outside"),
        ((0.0, 0.0), "boundary"),
    ],
)
def test_point_in_polygon_returns_explicit_boundary_state(point, expected: str) -> None:
    square = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]
    assert point_in_polygon(point, square) == expected


def test_point_in_polygon_handles_full_containment_case_for_room_overlap() -> None:
    outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    inner_vertex = (3.0, 3.0)
    assert point_in_polygon(inner_vertex, outer) == "inside"


def test_oriented_rect_corners_axis_aligned() -> None:
    assert oriented_rect_corners(0.0, 0.0, 4.0, 2.0, 0.0) == [
        (-2.0, -1.0),
        (2.0, -1.0),
        (2.0, 1.0),
        (-2.0, 1.0),
    ]


def test_sat_overlap_detects_overlap_and_full_containment_but_not_edge_touching() -> None:
    rect_a = oriented_rect_corners(0.0, 0.0, 4.0, 4.0, 0.0)
    rect_b = oriented_rect_corners(1.0, 1.0, 2.0, 2.0, 0.0)
    rect_c = oriented_rect_corners(4.0, 0.0, 4.0, 4.0, 0.0)

    assert sat_overlap(rect_a, rect_b) is True
    assert sat_overlap(rect_b, rect_a) is True
    assert sat_overlap(rect_a, rect_c) is False


def test_sat_overlap_detects_rotated_overlap() -> None:
    rect_a = oriented_rect_corners(0.0, 0.0, 4.0, 2.0, math.pi / 4.0)
    rect_b = oriented_rect_corners(1.0, 0.0, 4.0, 2.0, 0.0)

    assert sat_overlap(rect_a, rect_b) is True
