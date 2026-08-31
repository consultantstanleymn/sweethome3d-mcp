"""Dimension-line tool implementations."""

from __future__ import annotations

import math

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.primitives import MIN_DIMENSION_LENGTH
from sh3d_mcp.geometry.validation import check_scalars
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import make_dimension_line
from sh3d_mcp.tools.project import _validate_project_path


def add_dimension(
    project_path: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    offset: float = 20.0,
    label_angle: float = 0.0,
    visible_in_3d: bool = False,
) -> dict:
    """Add a dimension line to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not snap to existing geometry or infer offsets from nearby walls. Example: add_dimension(project_path='house.sh3d', x1=0, y1=0, x2=500, y2=0, offset=20)"""

    path = _validate_project_path(project_path)
    if not path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
            details={"project_path": str(path)},
        )

    check_scalars(x1=x1, y1=y1, x2=x2, y2=y2, offset=offset, label_angle=label_angle)

    document = Sh3dDocument.open(path)
    dimension_id = document.id_allocator.next_id("dimensionLine")
    dimension = make_dimension_line(
        dimension_id,
        x1,
        y1,
        x2,
        y2,
        offset,
        angle_rad=math.radians(label_angle % 360),
        visible_in_3d=visible_in_3d,
    )
    document.root.append(dimension)
    document.save()

    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if length < MIN_DIMENSION_LENGTH:
        raise Sh3dError(
            ErrorCode.DEGENERATE_DIMENSION,
            f"Dimension line length must be >= {MIN_DIMENSION_LENGTH} cm.",
            details={"length": length},
        )

    return {
        "ok": True,
        "dimension_id": dimension_id,
        "length": length,
    }
