"""MCP server registration for the Sweet Home 3D stdio server."""

from __future__ import annotations

from functools import wraps
import logging
import sys
from typing import Any, Callable, TypeVar

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.tools.dimensions import add_dimension as add_dimension_impl
from sh3d_mcp.tools.furniture import add_furniture as add_furniture_impl
from sh3d_mcp.tools.inspect import delete_element as delete_element_impl
from sh3d_mcp.tools.inspect import list_elements as list_elements_impl
from sh3d_mcp.tools.inspect import open_reference as open_reference_impl
from sh3d_mcp.tools.project import create_project as create_project_impl
from sh3d_mcp.tools.project import export_project as export_project_impl
from sh3d_mcp.tools.project import validate_project as validate_project_impl
from sh3d_mcp.tools.rooms import add_room as add_room_impl
from sh3d_mcp.tools.walls import add_wall as add_wall_impl

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as FastMCP


logging.basicConfig(stream=sys.stderr)

mcp = FastMCP("sweethome3d")

F = TypeVar("F", bound=Callable[..., dict[str, Any]])


def tool_wrapper(func: F) -> F:
    """Convert application exceptions into the documented MCP error envelope."""

    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except Sh3dError as exc:
            return exc.to_dict()
        except Exception as exc:  # pragma: no cover - exercised via MCP integration test
            return Sh3dError(ErrorCode.IO_ERROR, str(exc)).to_dict()

    return wrapped  # type: ignore[return-value]


@mcp.tool()
@tool_wrapper
def create_project(
    project_path: str,
    name: str,
    width: float | None = None,
    height: float | None = None,
    wall_height: float = 250.0,
    wall_thickness: float = 7.5,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not create multi-level homes or add furniture beyond the optional 4-wall rectangle footprint. Example: create_project(project_path='house.sh3d', name='House', width=800, height=600)"""

    return create_project_impl(
        project_path=project_path,
        name=name,
        width=width,
        height=height,
        wall_height=wall_height,
        wall_thickness=wall_thickness,
        overwrite=overwrite,
    )


@mcp.tool()
@tool_wrapper
def add_wall(
    project_path: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    thickness: float = 7.5,
    height: float | None = None,
    height_at_end: float | None = None,
    join: bool = True,
    allow_crossing: bool = False,
) -> dict[str, Any]:
    """Add a wall to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not create rooms or resolve unsupported multi-wall junctions beyond the documented pairwise join model. Example: add_wall(project_path='house.sh3d', x1=0, y1=0, x2=500, y2=0)"""

    return add_wall_impl(
        project_path=project_path,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        thickness=thickness,
        height=height,
        height_at_end=height_at_end,
        join=join,
        allow_crossing=allow_crossing,
    )


@mcp.tool()
@tool_wrapper
def add_room(
    project_path: str,
    points: list[tuple[float, float]],
    name: str | None = None,
    area_visible: bool = True,
    allow_overlap: bool = False,
) -> dict[str, Any]:
    """Add a room polygon to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not infer walls, repeat the closing point, or auto-split overlapping rooms. Example: add_room(project_path='house.sh3d', points=[(0,0),(500,0),(500,400),(0,400)], name='Kitchen')"""

    return add_room_impl(
        project_path=project_path,
        points=points,
        name=name,
        area_visible=area_visible,
        allow_overlap=allow_overlap,
    )


@mcp.tool()
@tool_wrapper
def add_furniture(
    project_path: str,
    catalog_id: str,
    x: float,
    y: float,
    rotation: float = 0.0,
    room_name: str | None = None,
    name: str | None = None,
    width: float | None = None,
    depth: float | None = None,
    height: float | None = None,
    elevation: float = 0.0,
    allow_overlap: bool = True,
) -> dict[str, Any]:
    """Add furniture to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not bind doors or windows to walls and cannot invent a missing 3D model or unsupported catalogue entry. Example: add_furniture(project_path='house.sh3d', catalog_id='eTeks#chair', x=120, y=240, rotation=90)"""

    return add_furniture_impl(
        project_path=project_path,
        catalog_id=catalog_id,
        x=x,
        y=y,
        rotation=rotation,
        room_name=room_name,
        name=name,
        width=width,
        depth=depth,
        height=height,
        elevation=elevation,
        allow_overlap=allow_overlap,
    )


@mcp.tool()
@tool_wrapper
def add_dimension(
    project_path: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    offset: float = 20.0,
    label_angle: float = 0.0,
    visible_in_3d: bool = False,
) -> dict[str, Any]:
    """Add a dimension line to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not snap to existing geometry or infer offsets from nearby walls. Example: add_dimension(project_path='house.sh3d', x1=0, y1=0, x2=500, y2=0, offset=20)"""

    return add_dimension_impl(
        project_path=project_path,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        offset=offset,
        label_angle=label_angle,
        visible_in_3d=visible_in_3d,
    )


@mcp.tool()
@tool_wrapper
def list_elements(
    project_path: str,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """List editable elements in a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not modify the archive or canonicalize element order. Example: list_elements(project_path='house.sh3d', kinds=['walls','rooms'])"""

    return list_elements_impl(project_path=project_path, kinds=kinds)


@mcp.tool()
@tool_wrapper
def export_project(
    project_path: str,
    destination_path: str | None = None,
) -> dict[str, Any]:
    """Finalize and rewrite a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not export OBJ, PNG, SVG, or any format other than .sh3d. Example: export_project(project_path='house.sh3d', destination_path='house-final.sh3d')"""

    return export_project_impl(project_path=project_path, destination_path=destination_path)


@mcp.tool()
@tool_wrapper
def open_reference(sample_sh3d_path: str) -> dict[str, Any]:
    """Inspect a reference .sh3d file and populate the in-process furniture catalogue cache. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not modify the sample archive or copy any content into another project. Example: open_reference(sample_sh3d_path='sample.sh3d')"""

    return open_reference_impl(sample_sh3d_path=sample_sh3d_path)


@mcp.tool()
@tool_wrapper
def validate_project(project_path: str) -> dict[str, Any]:
    """Validate an existing .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not modify the archive or rewrite canonical order. Example: validate_project(project_path='house.sh3d')"""

    return validate_project_impl(project_path=project_path)


@mcp.tool()
@tool_wrapper
def delete_element(project_path: str, element_id: str) -> dict[str, Any]:
    """Delete an editable element from a .sh3d project by id. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not delete unsupported tags or repair geometry beyond clearing inbound wall join references to a deleted wall. Example: delete_element(project_path='house.sh3d', element_id='wall2')"""

    return delete_element_impl(project_path=project_path, element_id=element_id)


def main() -> None:
    """Run the MCP server over the default stdio transport."""

    mcp.run()
