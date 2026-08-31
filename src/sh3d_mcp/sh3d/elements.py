"""Element factories and read-only element projections for Home.xml."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from sh3d_mcp.geometry.primitives import Pt, dist, orient, shoelace_signed_area

from .constants import KNOWN_ATTRS


@dataclass(frozen=True)
class WallView:
    """Read-only wall projection for inspection output."""

    id: str
    x_start: float
    y_start: float
    x_end: float
    y_end: float
    thickness: float
    height: float | None
    length: float
    wall_at_start: str | None
    wall_at_end: str | None


@dataclass(frozen=True)
class RoomView:
    """Read-only room projection for inspection output."""

    id: str
    name: str | None
    points: list[Pt]
    area_cm2: float
    is_convex: bool


@dataclass(frozen=True)
class FurnitureView:
    """Read-only furniture projection for inspection output."""

    id: str
    catalog_id: str | None
    name: str
    x: float
    y: float
    angle_degrees: float
    width: float
    depth: float
    height: float
    elevation: float
    has_model: bool
    room_name: str | None


@dataclass(frozen=True)
class DimensionView:
    """Read-only dimension-line projection for inspection output."""

    id: str
    x_start: float
    y_start: float
    x_end: float
    y_end: float
    offset: float
    length: float


def fmt(v: float) -> str:
    """Format a float with trimmed precision for stable readable XML output."""

    rounded = round(float(v), 6)
    if rounded == 0.0:
        rounded = 0.0
    return repr(rounded)


def make_wall(
    id,
    x1,
    y1,
    x2,
    y2,
    thickness,
    height=None,
    height_at_end=None,
    level=None,
) -> ET.Element:
    """Build a wall element with only the requested non-default attributes."""

    attrs = {
        "id": str(id),
        "xStart": fmt(x1),
        "yStart": fmt(y1),
        "xEnd": fmt(x2),
        "yEnd": fmt(y2),
        "thickness": fmt(thickness),
    }
    if level is not None:
        attrs["level"] = str(level)
    if height is not None:
        attrs["height"] = fmt(height)
    if height_at_end is not None:
        attrs["heightAtEnd"] = fmt(height_at_end)
    return _element("wall", attrs)


def make_room(id, points: list[Pt], name=None, area_visible=True, level=None) -> ET.Element:
    """Build a room element with implicit closure and one point child per vertex."""

    attrs: dict[str, str] = {"id": str(id)}
    if level is not None:
        attrs["level"] = str(level)
    if name is not None:
        attrs["name"] = str(name)
    if area_visible:
        attrs["areaVisible"] = "true"

    room = _element("room", attrs)
    for x, y in points:
        room.append(_element("point", {"x": fmt(x), "y": fmt(y)}))
    return room


def make_furniture(
    id,
    catalog_id,
    name,
    x,
    y,
    angle_rad,
    width,
    depth,
    height,
    elevation=0.0,
    model_entry=None,
    level=None,
) -> ET.Element:
    """Build a pieceOfFurniture element without dangling content references."""

    attrs = {
        "id": str(id),
        "name": str(name),
        "x": fmt(x),
        "y": fmt(y),
        "width": fmt(width),
        "depth": fmt(depth),
        "height": fmt(height),
    }
    if level is not None:
        attrs["level"] = str(level)
    if catalog_id is not None:
        attrs["catalogId"] = str(catalog_id)
    if angle_rad != 0.0:
        attrs["angle"] = fmt(angle_rad)
    if elevation != 0.0:
        attrs["elevation"] = fmt(elevation)
    if model_entry is not None:
        attrs["model"] = str(model_entry)
    return _element("pieceOfFurniture", attrs)


def make_dimension_line(
    id,
    x1,
    y1,
    x2,
    y2,
    offset,
    angle_rad=0.0,
    visible_in_3d=False,
) -> ET.Element:
    """Build a dimensionLine element with required geometry and non-default options."""

    attrs = {
        "id": str(id),
        "xStart": fmt(x1),
        "yStart": fmt(y1),
        "xEnd": fmt(x2),
        "yEnd": fmt(y2),
        "offset": fmt(offset),
    }
    if angle_rad != 0.0:
        attrs["angle"] = fmt(angle_rad)
    if visible_in_3d:
        attrs["visibleIn3D"] = "true"
    return _element("dimensionLine", attrs)


def wall_view(el) -> WallView:
    """Project a wall element into a read-only dataclass."""

    x_start = float(el.attrib["xStart"])
    y_start = float(el.attrib["yStart"])
    x_end = float(el.attrib["xEnd"])
    y_end = float(el.attrib["yEnd"])
    return WallView(
        id=el.attrib["id"],
        x_start=x_start,
        y_start=y_start,
        x_end=x_end,
        y_end=y_end,
        thickness=float(el.attrib["thickness"]),
        height=float(el.attrib["height"]) if "height" in el.attrib else None,
        length=dist((x_start, y_start), (x_end, y_end)),
        wall_at_start=el.attrib.get("wallAtStart"),
        wall_at_end=el.attrib.get("wallAtEnd"),
    )


def room_view(el) -> RoomView:
    """Project a room element into a read-only dataclass."""

    points = [(float(point.attrib["x"]), float(point.attrib["y"])) for point in el.findall("point")]
    area = abs(shoelace_signed_area(points))
    return RoomView(
        id=el.attrib["id"],
        name=el.attrib.get("name"),
        points=points,
        area_cm2=area,
        is_convex=_is_convex(points),
    )


def furniture_view(el) -> FurnitureView:
    """Project a furniture element into a read-only dataclass."""

    return FurnitureView(
        id=el.attrib["id"],
        catalog_id=el.attrib.get("catalogId"),
        name=el.attrib["name"],
        x=float(el.attrib["x"]),
        y=float(el.attrib["y"]),
        angle_degrees=math.degrees(float(el.attrib.get("angle", "0"))),
        width=float(el.attrib["width"]),
        depth=float(el.attrib["depth"]),
        height=float(el.attrib["height"]),
        elevation=float(el.attrib.get("elevation", "0")),
        has_model="model" in el.attrib,
        room_name=None,
    )


def dimension_view(el) -> DimensionView:
    """Project a dimensionLine element into a read-only dataclass."""

    x_start = float(el.attrib["xStart"])
    y_start = float(el.attrib["yStart"])
    x_end = float(el.attrib["xEnd"])
    y_end = float(el.attrib["yEnd"])
    return DimensionView(
        id=el.attrib["id"],
        x_start=x_start,
        y_start=y_start,
        x_end=x_end,
        y_end=y_end,
        offset=float(el.attrib["offset"]),
        length=dist((x_start, y_start), (x_end, y_end)),
    )


def _element(tag: str, attrs: dict[str, str]) -> ET.Element:
    """Build an element and assert its emitted attribute names are DTD-known."""

    unknown = set(attrs) - KNOWN_ATTRS[tag]
    if unknown:
        raise ValueError(f"Unknown attributes for {tag}: {sorted(unknown)}")
    return ET.Element(tag, attrs)


def _is_convex(points: list[Pt]) -> bool:
    """Return whether a polygon is convex, treating triangles as convex."""

    if len(points) < 4:
        return True

    signs: list[int] = []
    for index, point in enumerate(points):
        cross = orient(points[index - 1], point, points[(index + 1) % len(points)])
        if cross == 0.0:
            continue
        signs.append(1 if cross > 0 else -1)
    return not signs or all(sign == signs[0] for sign in signs)
