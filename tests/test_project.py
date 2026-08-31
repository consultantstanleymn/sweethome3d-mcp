from pathlib import Path

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import room_view, wall_view
from sh3d_mcp.tools.project import create_project


def test_create_project_builds_closed_rectangle_room_and_reciprocal_joins(tmp_path: Path) -> None:
    project_path = tmp_path / "house.sh3d"

    result = create_project(
        project_path=str(project_path),
        name="House",
        width=800.0,
        height=600.0,
        wall_thickness=7.5,
    )

    assert result["ok"] is True
    assert result["walls_created"] == 4
    assert result["rooms_created"] == 1
    assert result["wall_ids"] == ["wall0", "wall1", "wall2", "wall3"]
    assert result["room_ids"] == ["room0"]

    document = Sh3dDocument.open(project_path)

    walls = [wall_view(wall) for wall in document.root.findall("wall")]
    assert [(wall.x_start, wall.y_start, wall.x_end, wall.y_end) for wall in walls] == [
        (3.75, 3.75, 796.25, 3.75),
        (796.25, 3.75, 796.25, 596.25),
        (796.25, 596.25, 3.75, 596.25),
        (3.75, 596.25, 3.75, 3.75),
    ]

    room = room_view(document.root.find("room"))
    assert room.area_cm2 == (800.0 - 15.0) * (600.0 - 15.0)

    wall_by_id = {wall.attrib["id"]: wall for wall in document.root.findall("wall")}
    assert sum(
        1
        for wall in wall_by_id.values()
        for attr in ("wallAtStart", "wallAtEnd")
        if attr in wall.attrib
    ) == 8

    for wall in wall_by_id.values():
        wall_id = wall.attrib["id"]
        start_neighbor = wall_by_id[wall.attrib["wallAtStart"]]
        end_neighbor = wall_by_id[wall.attrib["wallAtEnd"]]
        assert wall_id in {start_neighbor.attrib.get("wallAtStart"), start_neighbor.attrib.get("wallAtEnd")}
        assert wall_id in {end_neighbor.attrib.get("wallAtStart"), end_neighbor.attrib.get("wallAtEnd")}


def test_create_project_existing_target_without_overwrite_raises_project_exists(tmp_path: Path) -> None:
    project_path = tmp_path / "house.sh3d"

    create_project(project_path=str(project_path), name="House")

    with pytest.raises(Sh3dError) as exc_info:
        create_project(project_path=str(project_path), name="House", overwrite=False)

    assert exc_info.value.code is ErrorCode.PROJECT_EXISTS
