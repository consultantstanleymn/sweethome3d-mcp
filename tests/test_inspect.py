import os
from pathlib import Path

from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY
from sh3d_mcp.tools.inspect import list_elements


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
