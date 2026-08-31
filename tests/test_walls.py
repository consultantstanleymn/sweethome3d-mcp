import hashlib
from pathlib import Path

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.tools.project import create_project
from sh3d_mcp.tools.walls import add_wall


def test_add_wall_joins_at_shared_corner_and_snaps_endpoint_within_tolerance(tmp_path: Path) -> None:
    project_path = tmp_path / "walls.sh3d"
    create_project(project_path=str(project_path), name="House")

    first = add_wall(
        project_path=str(project_path),
        x1=0.0,
        y1=0.0,
        x2=100.0,
        y2=0.0,
    )
    second = add_wall(
        project_path=str(project_path),
        x1=100.5,
        y1=0.0,
        x2=100.5,
        y2=80.0,
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["joined"]["start"] == "wall0"

    document = Sh3dDocument.open(project_path)
    walls = {wall.attrib["id"]: wall for wall in document.root.findall("wall")}
    assert walls["wall1"].attrib["wallAtStart"] == "wall0"
    assert walls["wall0"].attrib["wallAtEnd"] == "wall1"
    assert walls["wall1"].attrib["xStart"] == walls["wall0"].attrib["xEnd"] == "100.0"
    assert walls["wall1"].attrib["yStart"] == walls["wall0"].attrib["yEnd"] == "0.0"


def test_add_wall_duplicate_returns_documented_error_and_leaves_file_unchanged(tmp_path: Path) -> None:
    project_path = tmp_path / "walls.sh3d"
    create_project(project_path=str(project_path), name="House")
    add_wall(
        project_path=str(project_path),
        x1=0.0,
        y1=0.0,
        x2=100.0,
        y2=0.0,
    )
    before = hashlib.sha256(project_path.read_bytes()).hexdigest()

    try:
        add_wall(
            project_path=str(project_path),
            x1=0.0,
            y1=0.0,
            x2=100.0,
            y2=0.0,
        )
    except Sh3dError as exc:
        assert exc.code is ErrorCode.WALL_DUPLICATE
    else:
        raise AssertionError("Expected WALL_DUPLICATE")

    after = hashlib.sha256(project_path.read_bytes()).hexdigest()
    assert after == before
