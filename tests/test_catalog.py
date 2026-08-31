from pathlib import Path

from sh3d_mcp.catalog import BUILTIN_CATALOG, ReferenceCatalog, resolve_catalog_entry
from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY


def test_reference_catalog_extracts_dimensions_and_model_bytes_from_fixture(tmp_path: Path) -> None:
    project_path = tmp_path / "reference.sh3d"
    model_bytes = b"reference-model"
    archive.write_sh3d(
        project_path,
        {
            HOME_XML_ENTRY: b"""<?xml version='1.0'?>
<home version='5300' name='Reference' camera='topCamera' wallHeight='250'>
  <pieceOfFurniture id='furniture0' name='Reference Chair' catalogId='ref#chair'
      x='10' y='20' width='44' depth='45' height='91'
      model='models/1.obj' modelRotation='0 1 0 1 0 0 0 0 1'/>
</home>
""",
            "models/1.obj": model_bytes,
        },
    )

    catalog = ReferenceCatalog.from_project_path(project_path)
    entry = catalog.get("ref#chair")

    assert entry is not None
    assert entry.name == "Reference Chair"
    assert entry.width == 44.0
    assert entry.depth == 45.0
    assert entry.height == 91.0
    assert entry.model_rotation == "0 1 0 1 0 0 0 0 1"
    assert entry.model_bytes == model_bytes
    assert entry.model_entry_name == "models/1.obj"


def test_resolve_catalog_entry_prefers_reference_catalog_over_builtin(tmp_path: Path) -> None:
    project_path = tmp_path / "override.sh3d"
    archive.write_sh3d(
        project_path,
        {
            HOME_XML_ENTRY: b"""<?xml version='1.0'?>
<home version='5300' name='Reference' camera='topCamera' wallHeight='250'>
  <pieceOfFurniture id='furniture0' name='Reference Chair' catalogId='eTeks#chair'
      x='10' y='20' width='99' depth='88' height='77'/>
</home>
""",
        },
    )

    reference_catalog = ReferenceCatalog.from_project_path(project_path)
    resolved = resolve_catalog_entry("eTeks#chair", reference_catalog=reference_catalog)

    assert resolved is not None
    assert resolved.name == "Reference Chair"
    assert resolved.width == 99.0
    assert resolved.depth == 88.0
    assert resolved.height == 77.0
    assert resolved != BUILTIN_CATALOG["eTeks#chair"]
