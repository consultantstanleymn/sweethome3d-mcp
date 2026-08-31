"""Furniture tool implementations."""

from __future__ import annotations

import math
from pathlib import Path

from sh3d_mcp.catalog import BUILTIN_CATALOG, CatalogEntry, ReferenceCatalog, _REFERENCE_CACHE, resolve_catalog_entry
from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.primitives import point_in_polygon, polygon_bbox
from sh3d_mcp.geometry.validation import check_scalars, furniture_overlaps
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import make_furniture
from sh3d_mcp.tools.project import _validate_project_path


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
) -> dict:
    """Add furniture to a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not bind doors/windows to walls or guarantee 3D models for built-in catalogue ids. Example: add_furniture(project_path='house.sh3d', catalog_id='eTeks#chair', x=120, y=240, rotation=90)"""

    path = _validate_project_path(project_path)
    if not path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
            details={"project_path": str(path)},
        )

    check_scalars(x=x, y=y, width=width, depth=depth, height=height, elevation=elevation, rotation=rotation)
    document = Sh3dDocument.open(path)

    reference_catalog = _resolve_cached_reference_catalog(catalog_id)
    resolved = resolve_catalog_entry(catalog_id, reference_catalog=reference_catalog)
    width, depth, height, dimension_source = _resolve_dimensions(
        catalog_id=catalog_id,
        explicit_width=width,
        explicit_depth=depth,
        explicit_height=height,
        resolved=resolved,
    )
    check_scalars(width=width, depth=depth, height=height, elevation=elevation)

    angle_rad = math.radians(rotation % 360)
    warnings: list[str] = []

    if room_name is not None:
        _assert_room_contains_point(document, room_name, (x, y))

    furniture_id = document.id_allocator.next_id("furniture")
    model_entry_name = None
    if resolved is not None and resolved.model_bytes is not None and resolved.model_entry_name is not None:
        model_entry_name = _copy_model_bytes(document, furniture_id, resolved.model_entry_name, resolved.model_bytes)
    else:
        warnings.append(
            f"No 3D model available for '{catalog_id}'; the piece will appear in the plan but may not render in 3D."
        )

    furniture_name = name if name is not None else (resolved.name if resolved is not None else catalog_id)
    furniture = make_furniture(
        furniture_id,
        catalog_id,
        furniture_name,
        x,
        y,
        angle_rad,
        width,
        depth,
        height,
        elevation=elevation,
        model_entry=model_entry_name,
    )

    overlap_warnings = _check_furniture_overlap(document, furniture, allow_overlap=allow_overlap)
    warnings.extend(overlap_warnings)

    document.root.append(furniture)
    document.save()

    contained_room_name = room_name
    if contained_room_name is None:
        contained_room_name = _find_containing_room_name(document, (x, y))

    return {
        "ok": True,
        "furniture_id": furniture_id,
        "catalog_id": catalog_id,
        "name": furniture_name,
        "x": x,
        "y": y,
        "rotation_degrees": rotation % 360,
        "width": width,
        "depth": depth,
        "height": height,
        "dimension_source": dimension_source,
        "model_included": model_entry_name is not None,
        "room_name": contained_room_name,
        "warnings": warnings,
    }


def _resolve_cached_reference_catalog(catalog_id: str) -> ReferenceCatalog | None:
    """Return the most recently cached reference catalog containing the requested id."""

    for catalog in reversed(list(_REFERENCE_CACHE.values())):
        if catalog.get(catalog_id) is not None:
            return catalog
    return None


def _resolve_dimensions(
    *,
    catalog_id: str,
    explicit_width: float | None,
    explicit_depth: float | None,
    explicit_height: float | None,
    resolved: CatalogEntry | None,
) -> tuple[float, float, float, str]:
    """Resolve dimensions with explicit values taking precedence over reference/builtin values."""

    if explicit_width is not None and explicit_depth is not None and explicit_height is not None:
        return explicit_width, explicit_depth, explicit_height, "explicit_dimensions"

    if resolved is None:
        if any(value is not None for value in (explicit_width, explicit_depth, explicit_height)):
            raise Sh3dError(
                ErrorCode.INVALID_ARGUMENT,
                "Partial explicit dimensions require a resolvable catalogue entry for the remaining values.",
                details={
                    "catalog_id": catalog_id,
                    "width": explicit_width,
                    "depth": explicit_depth,
                    "height": explicit_height,
                },
            )
        raise Sh3dError(
            ErrorCode.UNKNOWN_CATALOG_ID,
            f"Unknown catalog_id '{catalog_id}'.",
            details={"catalog_id": catalog_id, "available_ids": sorted(BUILTIN_CATALOG)},
        )

    width = explicit_width if explicit_width is not None else resolved.width
    depth = explicit_depth if explicit_depth is not None else resolved.depth
    height = explicit_height if explicit_height is not None else resolved.height
    if any(value is None for value in (width, depth, height)):
        raise Sh3dError(
            ErrorCode.INVALID_ARGUMENT,
            "Partial explicit dimensions require a resolvable catalogue entry for the remaining values.",
            details={
                "catalog_id": catalog_id,
                "width": explicit_width,
                "depth": explicit_depth,
                "height": explicit_height,
            },
        )

    if resolved.model_bytes is not None:
        return width, depth, height, "reference_catalog"
    return width, depth, height, "builtin_table"


def _assert_room_contains_point(document: Sh3dDocument, room_name: str, point: tuple[float, float]) -> None:
    """Enforce the documented room_name placement assertion semantics."""

    matching_rooms = [room for room in document.root.findall("room") if room.attrib.get("name") == room_name]
    if not matching_rooms:
        raise Sh3dError(
            ErrorCode.ELEMENT_NOT_FOUND,
            f"room_name '{room_name}' does not resolve to any room.",
            details={"room_name": room_name},
        )
    if len(matching_rooms) > 1:
        raise Sh3dError(
            ErrorCode.AMBIGUOUS_NAME,
            f"room_name '{room_name}' matches more than one room.",
            details={"room_name": room_name, "matches": [room.attrib.get('id') for room in matching_rooms]},
        )

    room = matching_rooms[0]
    room_points = [(float(p.attrib["x"]), float(p.attrib["y"])) for p in room.findall("point")]
    location = point_in_polygon(point, room_points)
    if location not in {"inside", "boundary"}:
        min_x, min_y, max_x, max_y = polygon_bbox(room_points)
        raise Sh3dError(
            ErrorCode.INVALID_ARGUMENT,
            f"Point {point} is not inside room '{room_name}'.",
            details={
                "room_name": room_name,
                "room_id": room.attrib.get("id"),
                "room_bbox": {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y},
            },
        )


def _copy_model_bytes(document: Sh3dDocument, furniture_id: str, source_entry_name: str, model_bytes: bytes) -> str:
    """Copy reference model bytes into the target archive under a fresh entry name."""

    suffix = Path(source_entry_name).suffix
    candidate = f"models/{furniture_id}{suffix}"
    index = 1
    while candidate in document.entries:
        candidate = f"models/{furniture_id}-{index}{suffix}"
        index += 1
    document.entries[candidate] = model_bytes
    return candidate


def _check_furniture_overlap(document: Sh3dDocument, furniture, allow_overlap: bool) -> list[str]:
    """Return overlap warnings or raise when overlap is disallowed."""

    new_piece = {
        "x": float(furniture.attrib["x"]),
        "y": float(furniture.attrib["y"]),
        "width": float(furniture.attrib["width"]),
        "depth": float(furniture.attrib["depth"]),
        "angle": float(furniture.attrib.get("angle", "0")),
        "elevation": float(furniture.attrib.get("elevation", "0")),
        "height": float(furniture.attrib["height"]),
    }
    warnings: list[str] = []
    for existing in document.root.findall("pieceOfFurniture"):
        existing_piece = {
            "x": float(existing.attrib["x"]),
            "y": float(existing.attrib["y"]),
            "width": float(existing.attrib["width"]),
            "depth": float(existing.attrib["depth"]),
            "angle": float(existing.attrib.get("angle", "0")),
            "elevation": float(existing.attrib.get("elevation", "0")),
            "height": float(existing.attrib["height"]),
        }
        overlaps, details = furniture_overlaps(new_piece, existing_piece)
        if overlaps:
            message = f"Furniture footprint overlaps existing furniture '{existing.attrib.get('id')}'."
            if details and "note" in details:
                message = f"{message} {details['note']}"
            if allow_overlap:
                warnings.append(message)
            else:
                raise Sh3dError(
                    ErrorCode.FURNITURE_OVERLAPS,
                    message,
                    details={"existing_furniture_id": existing.attrib.get("id")},
                )
    return warnings


def _find_containing_room_name(document: Sh3dDocument, point: tuple[float, float]) -> str | None:
    """Return the name of the first room containing the point, if any."""

    for room in document.root.findall("room"):
        room_points = [(float(p.attrib["x"]), float(p.attrib["y"])) for p in room.findall("point")]
        if point_in_polygon(point, room_points) in {"inside", "boundary"}:
            return room.attrib.get("name")
    return None
