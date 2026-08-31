from sh3d_mcp.sh3d.constants import HOME_CHILD_ORDER, KNOWN_TAGS


def test_home_child_order_has_no_duplicates_and_contains_required_tags() -> None:
    assert len(HOME_CHILD_ORDER) == len(set(HOME_CHILD_ORDER))
    assert "wall" in HOME_CHILD_ORDER
    assert "room" in HOME_CHILD_ORDER
    assert "dimensionLine" in HOME_CHILD_ORDER


def test_known_tags_is_superset_of_home_child_order() -> None:
    assert set(HOME_CHILD_ORDER).issubset(KNOWN_TAGS)
