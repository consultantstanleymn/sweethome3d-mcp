"""Project-level tool implementations."""

from __future__ import annotations

from pathlib import Path

from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.validation import check_scalars, furniture_overlaps, rooms_overlap, validate_room_points, wall_is_duplicate, walls_properly_cross
from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import CONTENT_DIGESTS_ENTRY, HOME_XML_ENTRY, LEGACY_HOME_ENTRY
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


def export_project(project_path: str, destination_path: str | None = None) -> dict:
    """Finalize and rewrite a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not export OBJ, PNG, SVG, or any format other than .sh3d. Example: export_project(project_path='house.sh3d', destination_path='house-final.sh3d')"""

    source_path = _validate_project_path(project_path)
    if not source_path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {source_path}",
            details={"project_path": str(source_path)},
        )

    target_path = source_path if destination_path is None else _validate_project_path(destination_path)
    source_entries = archive.read_entries(source_path)
    document = Sh3dDocument.open(source_path)

    validation = _validate_document(document)
    bytes_written = document.save(target_path)
    entries_written = [HOME_XML_ENTRY, *sorted(document.entries)]

    result = {
        "ok": True,
        "project_path": str(target_path),
        "bytes_written": bytes_written,
        "entries": entries_written,
        "validation": validation,
        "counts": {
            "walls": len(document.root.findall("wall")),
            "rooms": len(document.root.findall("room")),
            "furniture": len(document.root.findall("pieceOfFurniture")),
            "dimensions": len(document.root.findall("dimensionLine")),
        },
    }
    if any(name in source_entries for name in (LEGACY_HOME_ENTRY, CONTENT_DIGESTS_ENTRY)):
        result["note"] = (
            "Legacy 'Home' and 'ContentDigests' entries are not written; Sweet Home 3D 6+ reads Home.xml in priority."
        )
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


def _validate_document(document: Sh3dDocument) -> dict:
    """Run the export-time validation pass directly over the current document tree."""

    errors: list[dict] = []
    warnings: list[str] = []

    walls = document.root.findall("wall")
    rooms = document.root.findall("room")
    furniture = document.root.findall("pieceOfFurniture")
    dimensions = document.root.findall("dimensionLine")

    for wall in walls:
        try:
            check_scalars(
                x1=float(wall.attrib["xStart"]),
                y1=float(wall.attrib["yStart"]),
                x2=float(wall.attrib["xEnd"]),
                y2=float(wall.attrib["yEnd"]),
                thickness=float(wall.attrib["thickness"]),
                height=float(wall.attrib["height"]) if "height" in wall.attrib else None,
                height_at_end=float(wall.attrib["heightAtEnd"]) if "heightAtEnd" in wall.attrib else None,
            )
        except Sh3dError as exc:
            errors.append({**exc.to_dict()["error"], "element_id": wall.attrib.get("id")})

    for index, wall_a in enumerate(walls):
        start_a = (float(wall_a.attrib["xStart"]), float(wall_a.attrib["yStart"]))
        end_a = (float(wall_a.attrib["xEnd"]), float(wall_a.attrib["yEnd"]))
        for wall_b in walls[index + 1 :]:
            start_b = (float(wall_b.attrib["xStart"]), float(wall_b.attrib["yStart"]))
            end_b = (float(wall_b.attrib["xEnd"]), float(wall_b.attrib["yEnd"]))
            is_duplicate, duplicate_details = wall_is_duplicate(start_a, end_a, start_b, end_b)
            if is_duplicate:
                errors.append(
                    {
                        "code": ErrorCode.WALL_DUPLICATE.value,
                        "message": "A collinear-overlapping wall already exists.",
                        "details": {
                            "element_ids": [wall_a.attrib.get("id"), wall_b.attrib.get("id")],
                            **(duplicate_details or {}),
                        },
                        "hint": None,
                    }
                )
            crosses, crossing_details = walls_properly_cross(start_a, end_a, start_b, end_b)
            if crosses:
                errors.append(
                    {
                        "code": ErrorCode.WALL_CROSSES_WALL.value,
                        "message": "Wall properly crosses another wall mid-span.",
                        "details": {
                            "element_ids": [wall_a.attrib.get("id"), wall_b.attrib.get("id")],
                            **(crossing_details or {}),
                        },
                        "hint": None,
                    }
                )

    room_points_by_id: list[tuple[str | None, list[tuple[float, float]]]] = []
    for room in rooms:
        points = [(float(point.attrib["x"]), float(point.attrib["y"])) for point in room.findall("point")]
        try:
            cleaned_points, room_warnings = validate_room_points(points)
        except Sh3dError as exc:
            errors.append({**exc.to_dict()["error"], "element_id": room.attrib.get("id")})
            continue
        room_points_by_id.append((room.attrib.get("id"), cleaned_points))
        warnings.extend(room_warnings)

    for index, (room_id_a, points_a) in enumerate(room_points_by_id):
        for room_id_b, points_b in room_points_by_id[index + 1 :]:
            overlaps, overlap_details = rooms_overlap(points_a, points_b)
            if overlaps:
                errors.append(
                    {
                        "code": ErrorCode.ROOM_OVERLAPS.value,
                        "message": "Room overlaps an existing room beyond tolerance.",
                        "details": {"element_ids": [room_id_a, room_id_b], **(overlap_details or {})},
                        "hint": None,
                    }
                )

    for dimension in dimensions:
        try:
            check_scalars(
                x1=float(dimension.attrib["xStart"]),
                y1=float(dimension.attrib["yStart"]),
                x2=float(dimension.attrib["xEnd"]),
                y2=float(dimension.attrib["yEnd"]),
                offset=float(dimension.attrib["offset"]),
            )
        except Sh3dError as exc:
            errors.append({**exc.to_dict()["error"], "element_id": dimension.attrib.get("id")})

    for piece in furniture:
        try:
            check_scalars(
                x=float(piece.attrib["x"]),
                y=float(piece.attrib["y"]),
                width=float(piece.attrib["width"]),
                depth=float(piece.attrib["depth"]),
                height=float(piece.attrib["height"]),
                elevation=float(piece.attrib.get("elevation", "0")),
            )
        except Sh3dError as exc:
            errors.append({**exc.to_dict()["error"], "element_id": piece.attrib.get("id")})

    for index, piece_a in enumerate(furniture):
        mapped_a = _furniture_mapping(piece_a)
        for piece_b in furniture[index + 1 :]:
            overlaps, details = furniture_overlaps(mapped_a, _furniture_mapping(piece_b))
            if overlaps:
                message = f"Furniture footprint overlaps existing furniture '{piece_b.attrib.get('id')}'."
                if details and "note" in details:
                    message = f"{message} {details['note']}"
                warnings.append(message)

    return {"errors": errors, "warnings": warnings}


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


def _furniture_mapping(piece) -> dict[str, float]:
    """Adapt a furniture element to the geometry validator input shape."""

    return {
        "x": float(piece.attrib["x"]),
        "y": float(piece.attrib["y"]),
        "width": float(piece.attrib["width"]),
        "depth": float(piece.attrib["depth"]),
        "height": float(piece.attrib["height"]),
        "angle": float(piece.attrib.get("angle", "0")),
        "elevation": float(piece.attrib.get("elevation", "0")),
    }
