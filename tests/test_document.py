from pathlib import Path

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY
from sh3d_mcp.sh3d.document import Sh3dDocument


def test_create_save_open_preserves_home_name(tmp_path: Path) -> None:
    project_path = tmp_path / "project.sh3d"

    document = Sh3dDocument.create(project_path, name="Demo House")
    bytes_written = document.save()
    reopened = Sh3dDocument.open(project_path)

    assert bytes_written == project_path.stat().st_size
    assert reopened.root.attrib["name"] == "Demo House"


def test_open_missing_home_xml_raises_documented_error(tmp_path: Path) -> None:
    project_path = tmp_path / "legacy-only.sh3d"
    archive.write_sh3d(project_path, {"Home": b"legacy-bytes"})

    with pytest.raises(Sh3dError) as exc_info:
        Sh3dDocument.open(project_path)

    assert exc_info.value.code is ErrorCode.MISSING_HOME_XML
    assert "re-saved by Sweet Home 3D 6+ first" in exc_info.value.message


def test_open_malformed_home_xml_raises_documented_error(tmp_path: Path) -> None:
    project_path = tmp_path / "malformed.sh3d"
    archive.write_sh3d(project_path, {HOME_XML_ENTRY: b"<home>"})

    with pytest.raises(Sh3dError) as exc_info:
        Sh3dDocument.open(project_path)

    assert exc_info.value.code is ErrorCode.MALFORMED_XML
