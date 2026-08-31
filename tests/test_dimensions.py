from pathlib import Path

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.tools.dimensions import add_dimension
from sh3d_mcp.tools.project import create_project


def test_add_dimension_zero_length_returns_documented_error(tmp_path: Path) -> None:
    project_path = tmp_path / "dimensions.sh3d"
    create_project(project_path=str(project_path), name="House")

    with pytest.raises(Sh3dError) as exc_info:
        add_dimension(
            project_path=str(project_path),
            x1=100.0,
            y1=200.0,
            x2=100.0,
            y2=200.0,
        )

    assert exc_info.value.code is ErrorCode.DEGENERATE_DIMENSION


def test_add_dimension_missing_project_raises_documented_not_found_error(tmp_path: Path) -> None:
    project_path = tmp_path / "missing.sh3d"

    with pytest.raises(Sh3dError) as exc_info:
        add_dimension(
            project_path=str(project_path),
            x1=10.0,
            y1=20.0,
            x2=110.0,
            y2=20.0,
        )

    assert exc_info.value.code is ErrorCode.PROJECT_NOT_FOUND


def test_add_dimension_emits_required_attributes_and_id(tmp_path: Path) -> None:
    project_path = tmp_path / "dimensions.sh3d"
    create_project(project_path=str(project_path), name="House")

    result = add_dimension(
        project_path=str(project_path),
        x1=10.0,
        y1=20.0,
        x2=110.0,
        y2=20.0,
    )

    assert result["ok"] is True

    document = Sh3dDocument.open(project_path)
    dimensions = document.root.findall("dimensionLine")
    assert len(dimensions) == 1

    attrs = dimensions[0].attrib
    assert set(attrs) == {"id", "xStart", "yStart", "xEnd", "yEnd", "offset"}
    assert attrs["id"] == result["dimension_id"]
