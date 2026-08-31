"""Room tool implementations."""

from __future__ import annotations

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.validation import rooms_overlap, validate_room_points
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import make_room
from sh3d_mcp.tools.project import _validate_project_path


def add_room(
    project_path: str,
    points: list[tuple[float, float]],
    name: str | None = None,
    area_visible: bool = True,
    allow_overlap: bool = False,
) -> dict:
    """Add a room polygon to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not infer walls or auto-split overlapping rooms. Example: add_room(project_path='house.sh3d', points=[(0,0),(500,0),(500,400),(0,400)], name='Kitchen')"""

    path = _validate_project_path(project_path)
    if not path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
            details={"project_path": str(path)},
        )

    cleaned_points, warnings = validate_room_points(points)
    document = Sh3dDocument.open(path)

    if name is not None:
        stripped_name = name.strip()
        if not stripped_name:
            raise Sh3dError(
                ErrorCode.INVALID_ARGUMENT,
                "name must be non-empty after stripping whitespace.",
            )
        name = stripped_name

    for existing_room in document.root.findall("room"):
        existing_points = [
            (float(point.attrib["x"]), float(point.attrib["y"]))
            for point in existing_room.findall("point")
        ]
        overlaps, overlap_details = rooms_overlap(cleaned_points, existing_points)
        if overlaps and not allow_overlap:
            raise Sh3dError(
                ErrorCode.ROOM_OVERLAPS,
                "Room overlaps an existing room beyond tolerance.",
                details={
                    "existing_room_id": existing_room.attrib.get("id"),
                    "existing_room_name": existing_room.attrib.get("name"),
                    **(overlap_details or {}),
                },
            )

    room_id = document.id_allocator.next_id("room")
    room = make_room(room_id, cleaned_points, name=name, area_visible=area_visible)
    document.root.append(room)
    document.save()

    area_cm2 = abs(_shoelace(cleaned_points))
    return {
        "ok": True,
        "room_id": room_id,
        "name": name,
        "point_count": len(cleaned_points),
        "area_cm2": area_cm2,
        "area_m2": area_cm2 / 10000.0,
        "warnings": warnings,
    }


def _shoelace(points: list[tuple[float, float]]) -> float:
    """Return polygon area in cm²."""

    area2 = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area2 += (point[0] * next_point[1]) - (next_point[0] * point[1])
    return area2 / 2.0
