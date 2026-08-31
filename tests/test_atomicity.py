import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.tools.dimensions import add_dimension
from sh3d_mcp.tools.furniture import add_furniture
from sh3d_mcp.tools.inspect import delete_element
from sh3d_mcp.tools.project import create_project
from sh3d_mcp.tools.rooms import add_room
from sh3d_mcp.tools.walls import add_wall
from tests.conftest import sha256


def test_create_project_failure_leaves_existing_file_unchanged(tmp_project) -> None:
    before = sha256(tmp_project)

    with pytest.raises(Sh3dError) as exc_info:
        create_project(
            project_path=str(tmp_project),
            name="House",
            width=800.0,
            overwrite=True,
        )

    assert exc_info.value.code is ErrorCode.INVALID_ARGUMENT
    assert sha256(tmp_project) == before


def test_add_wall_failure_leaves_file_unchanged(tmp_project) -> None:
    add_wall(project_path=str(tmp_project), x1=0.0, y1=0.0, x2=100.0, y2=0.0)
    before = sha256(tmp_project)

    with pytest.raises(Sh3dError) as exc_info:
        add_wall(project_path=str(tmp_project), x1=0.0, y1=0.0, x2=100.0, y2=0.0)

    assert exc_info.value.code is ErrorCode.WALL_DUPLICATE
    assert sha256(tmp_project) == before


def test_add_room_failure_leaves_file_unchanged(tmp_project) -> None:
    before = sha256(tmp_project)

    with pytest.raises(Sh3dError) as exc_info:
        add_room(
            project_path=str(tmp_project),
            points=[(0.0, 0.0), (20.0, 0.0), (10.0, 10.0), (20.0, 20.0), (0.0, 20.0), (10.0, 10.0)],
        )

    assert exc_info.value.code is ErrorCode.ROOM_SELF_INTERSECTS
    assert sha256(tmp_project) == before


def test_add_furniture_failure_leaves_file_unchanged(tmp_project) -> None:
    before = sha256(tmp_project)

    with pytest.raises(Sh3dError) as exc_info:
        add_furniture(project_path=str(tmp_project), catalog_id="unknown#thing", x=10.0, y=20.0)

    assert exc_info.value.code is ErrorCode.UNKNOWN_CATALOG_ID
    assert sha256(tmp_project) == before


def test_add_dimension_failure_leaves_file_unchanged(tmp_project) -> None:
    before = sha256(tmp_project)

    with pytest.raises(Sh3dError) as exc_info:
        add_dimension(
            project_path=str(tmp_project),
            x1=100.0,
            y1=200.0,
            x2=100.0,
            y2=200.0,
        )

    assert exc_info.value.code is ErrorCode.DEGENERATE_DIMENSION
    assert sha256(tmp_project) == before


def test_delete_element_failure_leaves_file_unchanged(tmp_project) -> None:
    before = sha256(tmp_project)

    with pytest.raises(Sh3dError) as exc_info:
        delete_element(project_path=str(tmp_project), element_id="missing-id")

    assert exc_info.value.code is ErrorCode.ELEMENT_NOT_FOUND
    assert sha256(tmp_project) == before
