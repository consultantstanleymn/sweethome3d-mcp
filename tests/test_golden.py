from pathlib import Path
import xml.etree.ElementTree as ET

from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY
from sh3d_mcp.sh3d.document import Sh3dDocument


def test_writer_output_is_tree_equivalent_to_minimal_home_fixture(tmp_path: Path) -> None:
    fixture_path = Path(__file__).resolve().parent / "data" / "minimal_home.xml"
    project_path = tmp_path / "minimal.sh3d"
    fixture_bytes = fixture_path.read_bytes()

    archive.write_sh3d(project_path, {HOME_XML_ENTRY: fixture_bytes})

    document = Sh3dDocument.open(project_path)
    document.save()

    saved_entries = archive.read_entries(project_path)
    expected_root = ET.fromstring(fixture_bytes)
    actual_root = ET.fromstring(saved_entries[HOME_XML_ENTRY])

    assert_xml_trees_equivalent(actual_root, expected_root)


def assert_xml_trees_equivalent(actual: ET.Element, expected: ET.Element) -> None:
    """Assert recursive XML equivalence by tag, attributes, text, and child order."""

    assert actual.tag == expected.tag
    assert actual.attrib == expected.attrib
    assert (actual.text or "").strip() == (expected.text or "").strip()
    assert len(actual) == len(expected)

    for actual_child, expected_child in zip(actual, expected):
        assert_xml_trees_equivalent(actual_child, expected_child)
