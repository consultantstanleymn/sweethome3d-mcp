from sh3d_mcp.errors import ErrorCode, Sh3dError

EXPECTED_ERROR_CODES = [
    "BAD_PATH",
    "PROJECT_NOT_FOUND",
    "PROJECT_EXISTS",
    "NOT_A_ZIP",
    "MISSING_HOME_XML",
    "MALFORMED_XML",
    "INVALID_ARGUMENT",
    "DEGENERATE_DIMENSION",
    "WALL_TOO_SHORT",
    "WALL_DUPLICATE",
    "WALL_CROSSES_WALL",
    "ROOM_TOO_FEW_POINTS",
    "ROOM_DEGENERATE",
    "ROOM_SELF_INTERSECTS",
    "ROOM_OVERLAPS",
    "FURNITURE_OVERLAPS",
    "UNKNOWN_CATALOG_ID",
    "ELEMENT_NOT_FOUND",
    "AMBIGUOUS_NAME",
    "UNSUPPORTED_FEATURE",
    "IO_ERROR",
]


def test_sh3d_error_to_dict_matches_documented_envelope() -> None:
    error = Sh3dError(
        code=ErrorCode.ROOM_TOO_FEW_POINTS,
        message="Room polygon has only 2 points; at least 3 are required.",
        details={"point_count": 2},
        hint="Pass at least 3 distinct points; do not repeat the first point.",
    )

    assert error.to_dict() == {
        "ok": False,
        "error": {
            "code": "ROOM_TOO_FEW_POINTS",
            "message": "Room polygon has only 2 points; at least 3 are required.",
            "details": {"point_count": 2},
            "hint": "Pass at least 3 distinct points; do not repeat the first point.",
        },
    }


def test_error_code_members_match_documented_set_exactly() -> None:
    assert [member.name for member in ErrorCode] == EXPECTED_ERROR_CODES
    assert [member.value for member in ErrorCode] == EXPECTED_ERROR_CODES
