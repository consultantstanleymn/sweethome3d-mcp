from pathlib import Path

from sh3d_mcp.sh3d.constants import KNOWN_ATTRS, KNOWN_TAGS
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.tools.dimensions import add_dimension
from sh3d_mcp.tools.furniture import add_furniture
from sh3d_mcp.tools.project import create_project
from sh3d_mcp.tools.rooms import add_room
from sh3d_mcp.tools.walls import add_wall


def test_emitted_elements_and_attributes_conform_to_known_dtd_tables(tmp_path: Path) -> None:
    project_path = tmp_path / "schema-conformance.sh3d"
    create_project(
        project_path=str(project_path),
        name="House",
        width=800.0,
        height=600.0,
        wall_thickness=7.5,
    )
    add_wall(
        project_path=str(project_path),
        x1=100.0,
        y1=100.0,
        x2=300.0,
        y2=100.0,
        height=240.0,
        join=False,
    )
    add_room(
        project_path=str(project_path),
        points=[(100.0, 100.0), (300.0, 100.0), (300.0, 250.0), (100.0, 250.0)],
        name="Office",
        allow_overlap=True,
    )
    add_furniture(
        project_path=str(project_path),
        catalog_id="eTeks#chair",
        x=150.0,
        y=150.0,
        rotation=90.0,
        elevation=10.0,
    )
    add_dimension(
        project_path=str(project_path),
        x1=100.0,
        y1=80.0,
        x2=300.0,
        y2=80.0,
        offset=20.0,
        label_angle=15.0,
        visible_in_3d=True,
    )

    document = Sh3dDocument.open(project_path)

    for element in document.root.iter():
        assert element.tag in KNOWN_TAGS
        assert set(element.attrib).issubset(KNOWN_ATTRS[element.tag])
