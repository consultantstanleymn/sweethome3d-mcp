from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_CHILD_ORDER, HOME_XML_ENTRY
from sh3d_mcp.sh3d.document import IdAllocator, Sh3dDocument, reorder_children


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


def test_reorder_children_sorts_home_children_by_dtd_order_with_unknown_last() -> None:
    root = ET.Element("home")
    for tag in reversed(HOME_CHILD_ORDER):
        root.append(ET.Element(tag))
    root.append(ET.Element("weirdTag"))

    reorder_children(root)

    assert [child.tag for child in root] == [*HOME_CHILD_ORDER, "weirdTag"]


def test_reorder_children_sorts_room_children_with_points_last() -> None:
    room = ET.Element("room")
    point_a = ET.Element("point", {"x": "0", "y": "0"})
    property_el = ET.Element("property", {"name": "n", "value": "v"})
    point_b = ET.Element("point", {"x": "1", "y": "1"})
    room.extend([point_a, property_el, point_b])

    root = ET.Element("home")
    root.append(room)

    reorder_children(root)

    assert [child.tag for child in room] == ["property", "point", "point"]


def test_id_allocator_fills_gaps_for_existing_ids_in_tree() -> None:
    root = ET.Element("home")
    root.append(ET.Element("wall", {"id": "wall0"}))
    root.append(ET.Element("room"))
    root.find("room").append(ET.Element("label", {"id": "wall2"}))

    allocator = IdAllocator(root)

    assert allocator.next_id("wall") == "wall1"
    assert allocator.next_id("wall") == "wall3"


def test_id_allocator_starts_unused_prefix_at_zero() -> None:
    document = Sh3dDocument.create(Path("unused.sh3d"), name="Demo")

    assert document.id_allocator.next_id("room") == "room0"


def test_id_allocator_never_reissues_same_value_for_same_prefix() -> None:
    document = Sh3dDocument.create(Path("repeat.sh3d"), name="Demo")

    first_id = document.id_allocator.next_id("wall")
    second_id = document.id_allocator.next_id("wall")

    assert first_id == "wall0"
    assert second_id == "wall1"
    assert first_id != second_id
