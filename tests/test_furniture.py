from pathlib import Path

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.tools.furniture import add_furniture
from sh3d_mcp.tools.project import create_project
from sh3d_mcp.tools.rooms import add_room


def test_add_furniture_unknown_catalog_without_dimensions_lists_available_ids(tmp_path: Path) -> None:
    project_path = tmp_path / "furniture.sh3d"
    create_project(project_path=str(project_path), name="House")

    with pytest.raises(Sh3dError) as exc_info:
        add_furniture(project_path=str(project_path), catalog_id="unknown#thing", x=10.0, y=20.0)

    assert exc_info.value.code is ErrorCode.UNKNOWN_CATALOG_ID
    assert "available_ids" in (exc_info.value.details or {})
    assert "eTeks#chair" in exc_info.value.details["available_ids"]


def test_add_furniture_builtin_catalog_emits_no_model_attribute(tmp_path: Path) -> None:
    project_path = tmp_path / "furniture.sh3d"
    create_project(project_path=str(project_path), name="House")

    result = add_furniture(project_path=str(project_path), catalog_id="eTeks#chair", x=10.0, y=20.0)
    document = Sh3dDocument.open(project_path)
    furniture = document.root.find("pieceOfFurniture")

    assert result["ok"] is True
    assert result["model_included"] is False
    assert furniture is not None
    assert "model" not in furniture.attrib


def test_add_furniture_room_name_must_contain_point_and_reports_room_bbox(tmp_path: Path) -> None:
    project_path = tmp_path / "furniture.sh3d"
    create_project(project_path=str(project_path), name="House")
    add_room(
        project_path=str(project_path),
        name="Kitchen",
        points=[(0.0, 0.0), (40.0, 0.0), (40.0, 40.0), (0.0, 40.0)],
        allow_overlap=True,
    )

    with pytest.raises(Sh3dError) as exc_info:
        add_furniture(
            project_path=str(project_path),
            catalog_id="eTeks#chair",
            x=100.0,
            y=100.0,
            room_name="Kitchen",
        )

    assert exc_info.value.code is ErrorCode.INVALID_ARGUMENT
    assert exc_info.value.details["room_bbox"] == {"min_x": 0.0, "min_y": 0.0, "max_x": 40.0, "max_y": 40.0}
