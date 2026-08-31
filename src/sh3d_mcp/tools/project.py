"""Project-level tool implementations."""

from __future__ import annotations

from pathlib import Path

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.validation import check_scalars
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import make_room, make_wall


def create_project(
    project_path: str,
    name: str,
    width: float | None = None,
    height: float | None = None,
    wall_height: float = 250.0,
    wall_thickness: float = 7.5,
    overwrite: bool = False,
) -> dict:
    """Create a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not create multi-level homes or any furniture. Example: create_project(project_path='house.sh3d', name='House', width=800, height=600)"""

    target_path = _validate_project_path(project_path)
    if target_path.exists() and not overwrite:
        raise Sh3dError(
            ErrorCode.PROJECT_EXISTS,
            f"Project already exists: {target_path}",
            details={"project_path": str(target_path)},
        )

    stripped_name = name.strip()
    if not stripped_name:
        raise Sh3dError(
            ErrorCode.INVALID_ARGUMENT,
            "name must be non-empty after stripping whitespace.",
        )

    if (width is None) != (height is None):
        raise Sh3dError(
            ErrorCode.INVALID_ARGUMENT,
            "width and height must be given together.",
            details={"width": width, "height": height},
        )

    if wall_height <= 0:
        raise Sh3dError(
            ErrorCode.DEGENERATE_DIMENSION,
            "wall_height must be > 0.",
            details={"wall_height": wall_height},
        )
    if wall_thickness <= 0:
        raise Sh3dError(
            ErrorCode.DEGENERATE_DIMENSION,
            "wall_thickness must be > 0.",
            details={"wall_thickness": wall_thickness},
        )

    if width is not None and height is not None:
        check_scalars(width=width, height=height, wall_thickness=wall_thickness)

    document = Sh3dDocument.create(target_path, stripped_name, wall_height=wall_height)

    wall_ids: list[str] = []
    room_ids: list[str] = []
    note: str | None = None

    if width is not None and height is not None:
        half_t = wall_thickness / 2.0
        walls = [
            make_wall("wall0", half_t, half_t, width - half_t, half_t, wall_thickness, height=wall_height),
            make_wall("wall1", width - half_t, half_t, width - half_t, height - half_t, wall_thickness, height=wall_height),
            make_wall("wall2", width - half_t, height - half_t, half_t, height - half_t, wall_thickness, height=wall_height),
            make_wall("wall3", half_t, height - half_t, half_t, half_t, wall_thickness, height=wall_height),
        ]
        _join_rectangle_walls(walls)
        for wall in walls:
            document.root.append(wall)
            wall_ids.append(wall.attrib["id"])

        room = make_room(
            "room0",
            [
                (wall_thickness, wall_thickness),
                (width - wall_thickness, wall_thickness),
                (width - wall_thickness, height - wall_thickness),
                (wall_thickness, height - wall_thickness),
            ],
            name=stripped_name,
        )
        document.root.append(room)
        room_ids.append(room.attrib["id"])
        note = "width/height were interpreted as exterior dimensions of a 4-wall rectangle."

    document.save()

    result = {
        "ok": True,
        "project_path": str(target_path),
        "name": stripped_name,
        "walls_created": len(wall_ids),
        "rooms_created": len(room_ids),
        "wall_ids": wall_ids,
        "room_ids": room_ids,
    }
    if note is not None:
        result["note"] = note
    return result


def _validate_project_path(project_path: str) -> Path:
    """Apply the documented .sh3d path rules for project tools."""

    path = Path(project_path).expanduser().resolve()
    if path.suffix.lower() != ".sh3d":
        raise Sh3dError(
            ErrorCode.BAD_PATH,
            "project_path must end with .sh3d.",
            details={"project_path": project_path},
        )
    if path.exists() and not path.is_file():
        raise Sh3dError(
            ErrorCode.BAD_PATH,
            "project_path points to a directory or non-regular file.",
            details={"project_path": str(path)},
        )
    return path


def _join_rectangle_walls(walls: list) -> None:
    """Set the closed-loop reciprocal wall joins for the canonical 4-wall rectangle."""

    walls[0].attrib["wallAtStart"] = walls[3].attrib["id"]
    walls[0].attrib["wallAtEnd"] = walls[1].attrib["id"]
    walls[1].attrib["wallAtStart"] = walls[0].attrib["id"]
    walls[1].attrib["wallAtEnd"] = walls[2].attrib["id"]
    walls[2].attrib["wallAtStart"] = walls[1].attrib["id"]
    walls[2].attrib["wallAtEnd"] = walls[3].attrib["id"]
    walls[3].attrib["wallAtStart"] = walls[2].attrib["id"]
    walls[3].attrib["wallAtEnd"] = walls[0].attrib["id"]
