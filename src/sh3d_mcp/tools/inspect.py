"""Read-only project inspection tools."""

from __future__ import annotations

from dataclasses import asdict, replace

from sh3d_mcp.catalog import ReferenceCatalog
from sh3d_mcp.errors import ErrorCode, Sh3dError
from sh3d_mcp.geometry.primitives import point_in_polygon
from sh3d_mcp.sh3d import archive
from sh3d_mcp.sh3d.constants import KNOWN_ATTRS, KNOWN_TAGS
from sh3d_mcp.sh3d.document import Sh3dDocument
from sh3d_mcp.sh3d.elements import dimension_view, furniture_view, room_view, wall_view
from sh3d_mcp.tools.project import _validate_project_path

EDITABLE_KINDS = {
    "walls": "wall",
    "rooms": "room",
    "furniture": "pieceOfFurniture",
    "dimensions": "dimensionLine",
}
EDITABLE_TAGS = frozenset(EDITABLE_KINDS.values())


def list_elements(
    project_path: str,
    kinds: list[str] | None = None,
) -> dict:
    """List editable elements in a .sh3d project. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not modify the archive or canonicalize element order. Example: list_elements(project_path='house.sh3d', kinds=['walls','rooms'])"""

    path = _validate_project_path(project_path)
    if not path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
            details={"project_path": str(path)},
        )

    selected_kinds = _normalize_kinds(kinds)
    document = Sh3dDocument.open(path)

    wall_views = [wall_view(element) for element in document.root.findall("wall")]
    room_views = [room_view(element) for element in document.root.findall("room")]
    furniture_views = _build_furniture_views(document)
    dimension_views = [dimension_view(element) for element in document.root.findall("dimensionLine")]

    result = {
        "ok": True,
        "name": document.root.attrib.get("name"),
        "version": document.root.attrib.get("version"),
        "wall_height_default": float(document.root.attrib["wallHeight"])
        if "wallHeight" in document.root.attrib
        else None,
        "level_count": len(document.root.findall("level")),
        "bounds": _compute_bounds(wall_views, room_views),
        "counts": {
            "walls": len(wall_views),
            "rooms": len(room_views),
            "furniture": len(furniture_views),
            "dimensions": len(dimension_views),
        },
        "unsupported_elements_present": _unsupported_tags(document),
    }

    if "walls" in selected_kinds:
        result["walls"] = [asdict(view) for view in wall_views]
    if "rooms" in selected_kinds:
        result["rooms"] = [asdict(view) for view in room_views]
    if "furniture" in selected_kinds:
        result["furniture"] = [asdict(view) for view in furniture_views]
    if "dimensions" in selected_kinds:
        result["dimensions"] = [asdict(view) for view in dimension_views]

    return result


def open_reference(sample_sh3d_path: str) -> dict:
    """Inspect a reference .sh3d file and populate the in-process furniture catalogue cache. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not modify the sample archive or copy any content into another project. Example: open_reference(sample_sh3d_path='sample.sh3d')"""

    path = _validate_project_path(sample_sh3d_path)
    if not path.exists():
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
            details={"project_path": str(path)},
        )

    entries = archive.read_entries(path)
    document = Sh3dDocument.open(path)
    reference_catalog = ReferenceCatalog.from_project_path(path)
    tag_counts = _tag_census(document)
    unknown_tags, unknown_attributes = _unknown_schema_items(document)

    return {
        "ok": True,
        "entry_names": list(entries),
        "home": dict(document.root.attrib),
        "tag_counts": tag_counts,
        "unknown_tags": unknown_tags,
        "unknown_attributes": unknown_attributes,
        "catalog_entries": {
            catalog_id: {
                "name": entry.name,
                "width": entry.width,
                "depth": entry.depth,
                "height": entry.height,
                "model_rotation": entry.model_rotation,
                "has_model": entry.model_bytes is not None,
                "model_entry_name": entry.model_entry_name,
            }
            for catalog_id, entry in sorted(reference_catalog.entries.items())
        },
    }


def _normalize_kinds(kinds: list[str] | None) -> list[str]:
    """Validate the optional kind filter against the documented editable subsets."""

    if kinds is None:
        return ["walls", "rooms", "furniture", "dimensions"]

    invalid = [kind for kind in kinds if kind not in EDITABLE_KINDS]
    if invalid:
        raise Sh3dError(
            ErrorCode.INVALID_ARGUMENT,
            "kinds must be a subset of ['walls', 'rooms', 'furniture', 'dimensions'].",
            details={"invalid_kinds": invalid},
        )
    return kinds


def _build_furniture_views(document: Sh3dDocument) -> list:
    """Project furniture elements and resolve room_name by point-in-polygon."""

    rooms = [room_view(element) for element in document.root.findall("room")]
    views = []
    for element in document.root.findall("pieceOfFurniture"):
        base_view = furniture_view(element)
        room_name = _find_containing_room_name(rooms, (base_view.x, base_view.y))
        views.append(replace(base_view, room_name=room_name))
    return views


def _find_containing_room_name(rooms: list, point: tuple[float, float]) -> str | None:
    """Return the first room name whose polygon contains the point."""

    for room in rooms:
        if point_in_polygon(point, room.points) in {"inside", "boundary"}:
            return room.name
    return None


def _compute_bounds(walls: list, rooms: list) -> dict[str, float | None]:
    """Compute document bounds from wall endpoints and room points only."""

    xs: list[float] = []
    ys: list[float] = []

    for wall in walls:
        xs.extend([wall.x_start, wall.x_end])
        ys.extend([wall.y_start, wall.y_end])
    for room in rooms:
        for x, y in room.points:
            xs.append(x)
            ys.append(y)

    if not xs:
        return {"min_x": None, "min_y": None, "max_x": None, "max_y": None}

    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
    }


def _unsupported_tags(document: Sh3dDocument) -> list[str]:
    """Return sorted non-editable tags present anywhere under the home root."""

    tags = {element.tag for element in document.root.iter()}
    tags.discard(document.root.tag)
    return sorted(tag for tag in tags if tag not in EDITABLE_TAGS)


def _tag_census(document: Sh3dDocument) -> dict[str, int]:
    """Count every tag present in the document tree, including the home root."""

    counts: dict[str, int] = {}
    for element in document.root.iter():
        counts[element.tag] = counts.get(element.tag, 0) + 1
    return dict(sorted(counts.items()))


def _unknown_schema_items(document: Sh3dDocument) -> tuple[list[str], dict[str, list[str]]]:
    """Diff document tags and attributes against the known DTD-derived tables."""

    unknown_tags = sorted({element.tag for element in document.root.iter() if element.tag not in KNOWN_TAGS})
    unknown_attributes: dict[str, list[str]] = {}
    for element in document.root.iter():
        known_attrs = KNOWN_ATTRS.get(element.tag)
        if known_attrs is None:
            continue
        attrs = sorted(attr for attr in element.attrib if attr not in known_attrs)
        if attrs:
            unknown_attributes[element.tag] = attrs
    return unknown_tags, unknown_attributes
