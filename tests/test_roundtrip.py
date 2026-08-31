from pathlib import Path

from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY
from sh3d_mcp.sh3d.document import Sh3dDocument


def test_open_save_open_preserves_unknown_elements_attributes_and_entries(tmp_path: Path) -> None:
    project_path = tmp_path / "roundtrip.sh3d"
    model_bytes = b"dummy-model-bytes"
    home_xml = b"""<?xml version='1.0'?>
<home version='5300' name='Roundtrip' camera='topCamera' wallHeight='250'>
  <environment groundColor='123456' wallsAlpha='0.25'>
    <observerCamera attribute='observerCamera' x='1' y='2' z='3' yaw='0' pitch='0' fieldOfView='1.2'/>
  </environment>
  <compass x='10' y='20' diameter='30' northDirection='0.5' visible='true'/>
  <wall id='wall0' xStart='0' yStart='0' xEnd='100' yEnd='0' thickness='7.5' topColor='654321'>
    <baseboard attribute='leftSideBaseboard' thickness='1' height='8' color='111111'/>
  </wall>
  <polyline id='poly0' thickness='1'>
    <point x='0' y='0'/>
    <point x='25' y='25'/>
  </polyline>
  <label id='label0' x='50' y='50'>
    <text>Hi</text>
  </label>
</home>
"""
    archive.write_sh3d(
        project_path,
        {
            HOME_XML_ENTRY: home_xml,
            "models/1.obj": model_bytes,
        },
    )

    initial_document = Sh3dDocument.open(project_path)
    assert initial_document.entries["models/1.obj"] == model_bytes

    initial_document.save()
    reopened_document = Sh3dDocument.open(project_path)

    assert reopened_document.entries["models/1.obj"] == model_bytes
    assert set(reopened_document.entries) == {"models/1.obj"}

    root = reopened_document.root
    assert root.tag == "home"
    assert root.attrib["version"] == "5300"
    assert root.attrib["name"] == "Roundtrip"
    assert root.attrib["camera"] == "topCamera"
    assert root.attrib["wallHeight"] == "250"

    environment = root.find("environment")
    assert environment is not None
    assert environment.attrib == {"groundColor": "123456", "wallsAlpha": "0.25"}

    environment_observer_camera = environment.find("observerCamera")
    assert environment_observer_camera is not None
    assert environment_observer_camera.attrib == {
        "attribute": "observerCamera",
        "x": "1",
        "y": "2",
        "z": "3",
        "yaw": "0",
        "pitch": "0",
        "fieldOfView": "1.2",
    }

    compass = root.find("compass")
    assert compass is not None
    assert compass.attrib == {
        "x": "10",
        "y": "20",
        "diameter": "30",
        "northDirection": "0.5",
        "visible": "true",
    }

    wall = root.find("wall")
    assert wall is not None
    assert wall.attrib == {
        "id": "wall0",
        "xStart": "0",
        "yStart": "0",
        "xEnd": "100",
        "yEnd": "0",
        "thickness": "7.5",
        "topColor": "654321",
    }

    baseboard = wall.find("baseboard")
    assert baseboard is not None
    assert baseboard.attrib == {
        "attribute": "leftSideBaseboard",
        "thickness": "1",
        "height": "8",
        "color": "111111",
    }

    polyline = root.find("polyline")
    assert polyline is not None
    assert polyline.attrib == {"id": "poly0", "thickness": "1"}
    polyline_points = polyline.findall("point")
    assert len(polyline_points) == 2
    assert [point.attrib for point in polyline_points] == [
        {"x": "0", "y": "0"},
        {"x": "25", "y": "25"},
    ]

    label = root.find("label")
    assert label is not None
    assert label.attrib == {"id": "label0", "x": "50", "y": "50"}

    text = label.find("text")
    assert text is not None
    assert text.text == "Hi"
