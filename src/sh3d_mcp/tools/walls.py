"""Wall tool implementations."""

from __future__ import annotations

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.joins import join_new_wall
from sh3d_mcp.geometry.validation import (
    check_scalars,
    wall_is_duplicate,
    walls_properly_cross,
)
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import make_wall
from sh3d_mcp.tools.project import _validate_project_path


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
) -> dict:
    """Add a wall to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not create rooms or automatically resolve wall crossings beyond optional warnings. Example: add_wall(project_path='house.sh3d', x1=0, y1=0, x2=500, y2=0)"""

    path = _validate_project_path(project_path)
    if not path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
            details={"project_path": str(path)},
        )

    if height_at_end is not None and height is None:
        raise Sh3dError(
            ErrorCode.INVALID_ARGUMENT,
            "height_at_end requires height to also be set.",
            details={"height": height, "height_at_end": height_at_end},
        )

    check_scalars(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        thickness=thickness,
        height=height,
        height_at_end=height_at_end,
    )

    document = Sh3dDocument.open(path)
    new_start = (x1, y1)
    new_end = (x2, y2)
    warnings: list[str] = []

    for existing in document.root.findall("wall"):
        existing_start = (float(existing.attrib["xStart"]), float(existing.attrib["yStart"]))
        existing_end = (float(existing.attrib["xEnd"]), float(existing.attrib["yEnd"]))

        is_duplicate, duplicate_details = wall_is_duplicate(new_start, new_end, existing_start, existing_end)
        if is_duplicate:
            raise Sh3dError(
                ErrorCode.WALL_DUPLICATE,
                "A collinear-overlapping wall already exists.",
                details=duplicate_details,
            )

        crosses, crossing_details = walls_properly_cross(new_start, new_end, existing_start, existing_end)
        if crosses:
            if allow_crossing:
                warnings.append("New wall properly crosses an existing wall mid-span.")
            else:
                raise Sh3dError(
                    ErrorCode.WALL_CROSSES_WALL,
                    "New wall properly crosses an existing wall mid-span.",
                    details=crossing_details,
                )

    wall_id = document.id_allocator.next_id("wall")
    wall = make_wall(
        wall_id,
        x1,
        y1,
        x2,
        y2,
        thickness,
        height=height,
        height_at_end=height_at_end,
    )
    document.root.append(wall)

    joined = {"start": None, "end": None}
    if join:
        joined, join_warnings = join_new_wall(document, wall)
        warnings.extend(join_warnings)

    document.save()
    return {
        "ok": True,
        "wall_id": wall_id,
        "length": wall_view_length(wall),
        "joined": joined,
        "warnings": warnings,
    }


def wall_view_length(wall) -> float:
    """Compute wall length from a wall element without depending on the view adapter."""

    x1 = float(wall.attrib["xStart"])
    y1 = float(wall.attrib["yStart"])
    x2 = float(wall.attrib["xEnd"])
    y2 = float(wall.attrib["yEnd"])
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
