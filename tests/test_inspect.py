import os
from pathlib import Path

from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.tools.inspect import delete_element, list_elements, open_reference
from sh3d_mcp.tools.project import create_project, validate_project


def test_list_elements_reports_unsupported_tags_and_does_not_write(tmp_path: Path) -> None:
    project_path = tmp_path / "inspect.sh3d"
    home_xml = b"""<?xml version='1.0'?>
<home version='5300' name='Inspect' camera='topCamera' wallHeight='250'>
  <environment groundColor='123456' wallsAlpha='0.25'>
    <observerCamera attribute='observerCamera' x='1' y='2' z='3' yaw='0' pitch='0' fieldOfView='1.2'/>
  </environment>
  <wall id='wall0' xStart='0' yStart='0' xEnd='100' yEnd='0' thickness='7.5'/>
  <room id='room0' name='Kitchen' areaVisible='true'>
    <point x='0' y='0'/>
    <point x='100' y='0'/>
    <point x='100' y='100'/>
    <point x='0' y='100'/>
  </room>
  <pieceOfFurniture id='furniture0' catalogId='eTeks#chair' name='Chair' x='50' y='50' width='45' depth='45' height='90'/>
  <dimensionLine id='dimensionLine0' xStart='0' yStart='0' xEnd='100' yEnd='0' offset='20'/>
</home>
"""
    archive.write_sh3d(project_path, {HOME_XML_ENTRY: home_xml})

    before_mtime = os.path.getmtime(project_path)
    result = list_elements(project_path=str(project_path))
    after_mtime = os.path.getmtime(project_path)

    assert result["ok"] is True
    assert result["counts"] == {"walls": 1, "rooms": 1, "furniture": 1, "dimensions": 1}
    assert "environment" in result["unsupported_elements_present"]
    assert "observerCamera" in result["unsupported_elements_present"]
    assert result["furniture"][0]["room_name"] == "Kitchen"
    assert result["bounds"] == {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 100.0}
    assert after_mtime == before_mtime


def test_open_reference_reports_unknown_tags_and_populates_catalog(tmp_path: Path) -> None:
    project_path = tmp_path / "reference.sh3d"
    model_bytes = b"reference-model"
    home_xml = b"""<?xml version='1.0'?>
<home version='5300' name='Reference' camera='topCamera' wallHeight='250'>
  <futureThing/>
  <pieceOfFurniture id='furniture0' catalogId='custom#chair' name='Reference Chair'
                    x='50' y='50' width='45' depth='47' height='91' model='models/1.obj'/>
</home>
"""
    archive.write_sh3d(
        project_path,
        {
            HOME_XML_ENTRY: home_xml,
            "models/1.obj": model_bytes,
        },
    )

    before_mtime = os.path.getmtime(project_path)
    result = open_reference(sample_sh3d_path=str(project_path))
    after_mtime = os.path.getmtime(project_path)

    assert result["ok"] is True
    assert result["unknown_tags"] == ["futureThing"]
    assert result["entry_names"] == [HOME_XML_ENTRY, "models/1.obj"]
    assert result["home"] == {
        "version": "5300",
        "name": "Reference",
        "camera": "topCamera",
        "wallHeight": "250",
    }
    assert result["tag_counts"]["home"] == 1
    assert result["tag_counts"]["pieceOfFurniture"] == 1
    assert result["catalog_entries"]["custom#chair"] == {
        "name": "Reference Chair",
        "width": 45.0,
        "depth": 47.0,
        "height": 91.0,
        "model_rotation": "1 0 0 0 1 0 0 0 1",
        "has_model": True,
        "model_entry_name": "models/1.obj",
    }
    assert after_mtime == before_mtime


def test_delete_joined_wall_clears_neighbor_references_and_keeps_project_valid(tmp_path: Path) -> None:
    project_path = tmp_path / "delete-wall.sh3d"
    create_project(
        project_path=str(project_path),
        name="House",
        width=800.0,
        height=600.0,
        wall_thickness=7.5,
    )

    result = delete_element(project_path=str(project_path), element_id="wall1")

    assert result == {
        "ok": True,
        "deleted": "wall1",
        "kind": "wall",
        "references_cleared": ["wall0", "wall2"],
    }

    document = Sh3dDocument.open(project_path)
    wall_by_id = {wall.attrib["id"]: wall for wall in document.root.findall("wall")}

    assert "wall1" not in wall_by_id
    assert wall_by_id["wall0"].attrib.get("wallAtEnd") is None
    assert wall_by_id["wall2"].attrib.get("wallAtStart") is None
    assert wall_by_id["wall0"].attrib.get("wallAtStart") == "wall3"
    assert wall_by_id["wall3"].attrib.get("wallAtEnd") == "wall0"
    assert wall_by_id["wall2"].attrib.get("wallAtEnd") == "wall3"
    assert wall_by_id["wall3"].attrib.get("wallAtStart") == "wall2"

    validation = validate_project(project_path=str(project_path))

    assert validation == {"ok": True, "errors": [], "warnings": []}
