from pathlib import Path

from sh3d_mcp.geometry.joins import join_new_wall
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import make_wall


def test_join_new_wall_leaves_third_wall_unjoined_and_returns_t_junction_warning() -> None:
    document = Sh3dDocument.create(Path("joins.sh3d"), name="Joins")

    wall0 = make_wall("wall0", 0.0, 0.0, 10.0, 0.0, 7.5)
    wall1 = make_wall("wall1", 10.0, 0.0, 10.0, 10.0, 7.5)
    document.root.extend([wall0, wall1])

    joined, warnings = join_new_wall(document, wall1)
    assert joined == {"start": "wall0", "end": None}
    assert warnings == []
    assert wall1.attrib["wallAtStart"] == "wall0"
    assert wall0.attrib["wallAtEnd"] == "wall1"

    wall2 = make_wall("wall2", 10.5, 0.0, 20.0, 0.0, 7.5)
    document.root.append(wall2)

    joined, warnings = join_new_wall(document, wall2)

    assert joined == {"start": None, "end": None}
    assert warnings == [
        "Endpoint at (10.5,0.0) already has 2 walls joined; this wall's end was left unjoined (Sweet Home 3D supports only pairwise wall joins)."
    ]
    assert "wallAtStart" not in wall2.attrib
    assert wall0.attrib["wallAtEnd"] == "wall1"
    assert wall1.attrib["wallAtStart"] == "wall0"
