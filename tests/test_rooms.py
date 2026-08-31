from pathlib import Path

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.tools.project import create_project
from sh3d_mcp.tools.rooms import add_room


def test_add_room_drops_repeated_closing_point_with_documented_warning(tmp_path: Path) -> None:
    project_path = tmp_path / "rooms.sh3d"
    create_project(project_path=str(project_path), name="House")

    result = add_room(
        project_path=str(project_path),
        points=[(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0), (0.0, 0.0)],
        allow_overlap=True,
    )

    assert result["warnings"] == ["Dropped a repeated closing point; room closure is implicit."]
    assert result["point_count"] == 4


def test_add_room_self_intersecting_polygon_returns_documented_error(tmp_path: Path) -> None:
    project_path = tmp_path / "rooms.sh3d"
    create_project(project_path=str(project_path), name="House")

    with pytest.raises(Sh3dError) as exc_info:
        add_room(
            project_path=str(project_path),
            points=[(0.0, 0.0), (20.0, 0.0), (10.0, 10.0), (20.0, 20.0), (0.0, 20.0), (10.0, 10.0)],
        )

    assert exc_info.value.code is ErrorCode.ROOM_SELF_INTERSECTS


def test_add_room_edge_sharing_rectangles_do_not_report_overlap(tmp_path: Path) -> None:
    project_path = tmp_path / "rooms.sh3d"
    create_project(project_path=str(project_path), name="House")

    first = add_room(
        project_path=str(project_path),
        points=[(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)],
    )
    second = add_room(
        project_path=str(project_path),
        points=[(20.0, 0.0), (40.0, 0.0), (40.0, 10.0), (20.0, 10.0)],
    )

    assert first["ok"] is True
    assert second["ok"] is True


def test_add_room_fully_inside_existing_room_reports_overlap(tmp_path: Path) -> None:
    project_path = tmp_path / "rooms.sh3d"
    create_project(project_path=str(project_path), name="House")

    add_room(
        project_path=str(project_path),
        points=[(0.0, 0.0), (40.0, 0.0), (40.0, 40.0), (0.0, 40.0)],
    )

    with pytest.raises(Sh3dError) as exc_info:
        add_room(
            project_path=str(project_path),
            points=[(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)],
        )

    assert exc_info.value.code is ErrorCode.ROOM_OVERLAPS
