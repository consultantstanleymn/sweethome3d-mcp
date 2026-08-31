"""Wall endpoint joining helpers for Sweet Home 3D wall IDREF constraints."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from sh3d_mcp.geometry.primitives import EPS_POINT, JOIN_TOLERANCE, Pt, dist
from sh3d_mcp.sh3d.elements import fmt


def join_new_wall(doc, new_wall: ET.Element) -> tuple[dict[str, str | None], list[str]]:
    """Join a new wall's endpoints to nearby available wall ends, updating both sides."""

    joined: dict[str, str | None] = {"start": None, "end": None}
    warnings: list[str] = []

    level = new_wall.attrib.get("level")
    new_wall_id = new_wall.attrib.get("id")
    endpoints = (
        ("start", "wallAtStart", ("xStart", "yStart")),
        ("end", "wallAtEnd", ("xEnd", "yEnd")),
    )

    for endpoint_name, new_attr_name, coord_attrs in endpoints:
        point = _get_point(new_wall, coord_attrs)
        candidates = []
        had_occupied_candidate = False

        for wall in doc.root.findall("wall"):
            if wall is new_wall:
                continue
            if wall.attrib.get("level") != level:
                continue

            for which_end, wall_attr_name, wall_coord_attrs in (
                ("start", "wallAtStart", ("xStart", "yStart")),
                ("end", "wallAtEnd", ("xEnd", "yEnd")),
            ):
                other_point = _get_point(wall, wall_coord_attrs)
                distance = dist(point, other_point)
                if distance > JOIN_TOLERANCE:
                    continue

                current_ref = wall.attrib.get(wall_attr_name)
                if current_ref is not None and current_ref != new_wall_id:
                    had_occupied_candidate = True
                    continue

                candidates.append((distance, wall.attrib["id"], wall, wall_attr_name, other_point, which_end))

        candidates.sort(key=lambda item: (item[0], item[1]))
        if not candidates:
            if had_occupied_candidate:
                warnings.append(
                    "Endpoint at "
                    f"({fmt(point[0])},{fmt(point[1])}) already has 2 walls joined; "
                    "this wall's end was left unjoined (Sweet Home 3D supports only pairwise wall joins)."
                )
            continue

        distance, wall_id, wall, wall_attr_name, other_point, _which_end = candidates[0]
        new_wall.attrib[new_attr_name] = wall_id
        wall.attrib[wall_attr_name] = new_wall_id
        joined[endpoint_name] = wall_id

        if distance > 0.0:
            _set_point(new_wall, coord_attrs, other_point)
            if distance > EPS_POINT:
                warnings.append(
                    f"Snapped wall {endpoint_name} endpoint by {fmt(distance)} cm to join {wall_id}."
                )

    return joined, warnings


def _get_point(wall: ET.Element, coord_attrs: tuple[str, str]) -> Pt:
    """Read one wall endpoint from element attributes."""

    return float(wall.attrib[coord_attrs[0]]), float(wall.attrib[coord_attrs[1]])


def _set_point(wall: ET.Element, coord_attrs: tuple[str, str], point: Pt) -> None:
    """Write one wall endpoint back to element attributes."""

    wall.attrib[coord_attrs[0]] = fmt(point[0])
    wall.attrib[coord_attrs[1]] = fmt(point[1])
