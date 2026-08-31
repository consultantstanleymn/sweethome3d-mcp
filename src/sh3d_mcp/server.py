"""MCP server skeleton for the Sweet Home 3D stdio server."""

from __future__ import annotations

from functools import wraps
import logging
import sys
from typing import Any, Callable, TypeVar

from sh3d_mcp.errors import ErrorCode, Sh3dError

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as FastMCP


logging.basicConfig(stream=sys.stderr)

mcp = FastMCP("sweethome3d")

F = TypeVar("F", bound=Callable[..., dict[str, Any]])


def tool_wrapper(func: F) -> F:
    """Convert application exceptions into the documented MCP error envelope."""

    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except Sh3dError as exc:
            return exc.to_dict()
        except Exception as exc:  # pragma: no cover - exercised via MCP integration test
            return Sh3dError(ErrorCode.IO_ERROR, str(exc)).to_dict()

    return wrapped  # type: ignore[return-value]


@mcp.tool()
@tool_wrapper
def ping() -> dict[str, Any]:
    """Report server reachability. Lengths are in centimetres and rotations in degrees. The plan coordinate system uses y increasing downward. This tool does not inspect or modify .sh3d files. Example: ping()"""

    return {"ok": True, "message": "pong"}


def main() -> None:
    """Run the MCP server over the default stdio transport."""

    mcp.run()
