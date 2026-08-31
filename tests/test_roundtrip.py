import random
from pathlib import Path

from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.tools.dimensions import add_dimension
from sh3d_mcp.tools.furniture import add_furniture
from sh3d_mcp.tools.project import create_project
from sh3d_mcp.tools.rooms import add_room
from sh3d_mcp.tools.walls import add_wall


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


def test_seeded_roundtrip_fuzz_is_idempotent_and_preserves_element_counts(tmp_path: Path) -> None:
    rng = random.Random(20260831)

    for index in range(25):
        project_path = tmp_path / f"fuzz-{index}.sh3d"
        create_project(project_path=str(project_path), name=f"Fuzz {index}")

        for wall_index in range(rng.randint(0, 4)):
            x1 = 50.0 + wall_index * 250.0
            y1 = 40.0 + index * 5.0
            length = rng.uniform(60.0, 180.0)
            add_wall(
                project_path=str(project_path),
                x1=x1,
                y1=y1,
                x2=x1 + length,
                y2=y1,
                thickness=rng.uniform(7.5, 15.0),
                join=False,
            )

        room_centers: list[tuple[float, float, float, float, str]] = []
        for room_index in range(rng.randint(0, 3)):
            x = 20.0 + room_index * 220.0
            y = 120.0 + index * 12.0
            width = rng.uniform(80.0, 150.0)
            height = rng.uniform(80.0, 140.0)
            room_name = f"Room {room_index}"
            add_room(
                project_path=str(project_path),
                points=[
                    (x, y),
                    (x + width, y),
                    (x + width, y + height),
                    (x, y + height),
                ],
                name=room_name,
                allow_overlap=False,
            )
            room_centers.append((x, y, width, height, room_name))

        for furniture_index in range(rng.randint(0, 4)):
            if room_centers:
                room_x, room_y, room_width, room_height, room_name = room_centers[furniture_index % len(room_centers)]
                x = room_x + room_width / 2.0
                y = room_y + room_height / 2.0
            else:
                room_name = None
                x = 60.0 + furniture_index * 160.0
                y = 80.0 + index * 10.0
            add_furniture(
                project_path=str(project_path),
                catalog_id="eTeks#chair",
                x=x,
                y=y,
                rotation=rng.choice([0.0, 45.0, 90.0, 180.0, 270.0]),
                room_name=room_name,
                elevation=rng.choice([0.0, 10.0, 20.0]),
                allow_overlap=True,
            )

        for dimension_index in range(rng.randint(0, 3)):
            x1 = 30.0 + dimension_index * 210.0
            y1 = 90.0 + index * 8.0
            add_dimension(
                project_path=str(project_path),
                x1=x1,
                y1=y1,
                x2=x1 + rng.uniform(50.0, 170.0),
                y2=y1,
                offset=rng.choice([10.0, 20.0, 35.0]),
                label_angle=rng.choice([0.0, 15.0, 45.0]),
                visible_in_3d=rng.choice([False, True]),
            )

        first_document = Sh3dDocument.open(project_path)
        first_counts = _element_counts(first_document)
        first_document.save()
        first_bytes = project_path.read_bytes()

        reopened_document = Sh3dDocument.open(project_path)
        assert _element_counts(reopened_document) == first_counts
        reopened_document.save()
        second_bytes = project_path.read_bytes()

        final_document = Sh3dDocument.open(project_path)
        assert _element_counts(final_document) == first_counts
        assert second_bytes == first_bytes


def _element_counts(document: Sh3dDocument) -> dict[str, int]:
    """Return editable element counts for round-trip preservation assertions."""

    return {
        "walls": len(document.root.findall("wall")),
        "rooms": len(document.root.findall("room")),
        "furniture": len(document.root.findall("pieceOfFurniture")),
        "dimensions": len(document.root.findall("dimensionLine")),
    }
