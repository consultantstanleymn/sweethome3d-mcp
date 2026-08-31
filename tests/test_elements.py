import math

from sh3d_mcp.sh3d.constants import KNOWN_ATTRS
from sh3d_mcp.sh3d.elements import (
    dimension_view,
    furniture_view,
    make_dimension_line,
    make_furniture,
    make_room,
    make_wall,
    room_view,
    wall_view,
)


def test_make_wall_emits_only_required_attrs_when_height_is_none() -> None:
    wall = make_wall("wall0", 0.0, 0.0, 10.0, 0.0, 7.5)
    assert set(wall.attrib) == {"id", "xStart", "yStart", "xEnd", "yEnd", "thickness"}


def test_every_emitted_attribute_name_is_in_known_attrs() -> None:
    elements = [
        make_wall("wall0", 0.0, 0.0, 10.0, 0.0, 7.5, height=250.0, height_at_end=240.0, level="level0"),
        make_room("room0", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)], name="Room", level="level0"),
        make_furniture(
            "furniture0",
            "catalog0",
            "Chair",
            5.0,
            6.0,
            math.pi / 2.0,
            4.0,
            5.0,
            6.0,
            elevation=7.0,
            model_entry="models/1.obj",
            level="level0",
        ),
        make_dimension_line("dimensionLine0", 0.0, 0.0, 20.0, 0.0, 10.0, angle_rad=0.5, visible_in_3d=True),
    ]

    for element in elements:
        assert set(element.attrib).issubset(KNOWN_ATTRS[element.tag])
        for child in element:
            assert set(child.attrib).issubset(KNOWN_ATTRS[child.tag])


def test_make_room_does_not_repeat_first_point() -> None:
    room = make_room("room0", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    assert len(room.findall("point")) == 4


def test_wall_round_trips_through_view() -> None:
    wall = make_wall("wall0", 0.0, 0.0, 3.0, 4.0, 7.5, height=250.0)
    view = wall_view(wall)
    assert view.id == "wall0"
    assert view.x_start == 0.0
    assert view.y_end == 4.0
    assert view.thickness == 7.5
    assert view.height == 250.0
    assert view.length == 5.0


def test_room_round_trips_through_view() -> None:
    room = make_room("room0", [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)], name="Kitchen")
    view = room_view(room)
    assert view.id == "room0"
    assert view.name == "Kitchen"
    assert view.points == [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    assert view.area_cm2 == 200.0
    assert view.is_convex is True


def test_furniture_round_trips_through_view() -> None:
    furniture = make_furniture(
        "furniture0",
        "eTeks#chair",
        "Chair",
        12.0,
        24.0,
        math.pi / 2.0,
        45.0,
        45.0,
        90.0,
        elevation=5.0,
        model_entry="models/chair.obj",
    )
    view = furniture_view(furniture)
    assert view.id == "furniture0"
    assert view.catalog_id == "eTeks#chair"
    assert view.name == "Chair"
    assert view.x == 12.0
    assert view.y == 24.0
    assert math.isclose(view.angle_degrees, 90.0, abs_tol=1e-3)
    assert view.width == 45.0
    assert view.depth == 45.0
    assert view.height == 90.0
    assert view.elevation == 5.0
    assert view.has_model is True
    assert view.room_name is None


def test_dimension_round_trips_through_view() -> None:
    dimension = make_dimension_line("dimensionLine0", 0.0, 0.0, 30.0, 40.0, 20.0)
    view = dimension_view(dimension)
    assert view.id == "dimensionLine0"
    assert view.x_start == 0.0
    assert view.y_end == 40.0
    assert view.offset == 20.0
    assert view.length == 50.0
