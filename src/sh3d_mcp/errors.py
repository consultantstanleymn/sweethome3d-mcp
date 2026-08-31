"""Error taxonomy and structured error envelope for the Sweet Home 3D MCP server."""

from enum import Enum


class ErrorCode(str, Enum):
    """Documented error codes returned by tool implementations."""

    BAD_PATH = "BAD_PATH"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_EXISTS = "PROJECT_EXISTS"
    NOT_A_ZIP = "NOT_A_ZIP"
    MISSING_HOME_XML = "MISSING_HOME_XML"
    MALFORMED_XML = "MALFORMED_XML"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    DEGENERATE_DIMENSION = "DEGENERATE_DIMENSION"
    WALL_TOO_SHORT = "WALL_TOO_SHORT"
    WALL_DUPLICATE = "WALL_DUPLICATE"
    WALL_CROSSES_WALL = "WALL_CROSSES_WALL"
    ROOM_TOO_FEW_POINTS = "ROOM_TOO_FEW_POINTS"
    ROOM_DEGENERATE = "ROOM_DEGENERATE"
    ROOM_SELF_INTERSECTS = "ROOM_SELF_INTERSECTS"
    ROOM_OVERLAPS = "ROOM_OVERLAPS"
    FURNITURE_OVERLAPS = "FURNITURE_OVERLAPS"
    UNKNOWN_CATALOG_ID = "UNKNOWN_CATALOG_ID"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    AMBIGUOUS_NAME = "AMBIGUOUS_NAME"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    IO_ERROR = "IO_ERROR"


class Sh3dError(Exception):
    """Structured application error that can be converted into the documented envelope."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.hint = hint

    def to_dict(self) -> dict:
        """Return the exact error envelope documented in TOOL_INTERFACE.md §2."""

        return {
            "ok": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "hint": self.hint,
            },
        }
