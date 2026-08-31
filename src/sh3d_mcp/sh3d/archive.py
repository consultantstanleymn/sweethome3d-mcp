"""ZIP archive helpers for Sweet Home 3D .sh3d files."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from sh3d_mcp.errors import ErrorCode, Sh3dError

from .constants import HOME_XML_ENTRY

ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def read_entries(path: Path) -> dict[str, bytes]:
    """Read every ZIP entry from a .sh3d archive into memory."""

    try:
        with zipfile.ZipFile(path, "r") as archive:
            return {info.filename: archive.read(info.filename) for info in archive.infolist()}
    except FileNotFoundError as exc:
        raise Sh3dError(
            ErrorCode.PROJECT_NOT_FOUND,
            f"Project file does not exist: {path}",
        ) from exc
    except zipfile.BadZipFile as exc:
        raise Sh3dError(
            ErrorCode.NOT_A_ZIP,
            f"File is not a readable ZIP archive: {path}",
        ) from exc


def write_sh3d(path: Path, entries: dict[str, bytes], compress: bool = True) -> int:
    """Write a .sh3d archive atomically, with Home.xml first and remaining entries sorted."""

    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    tmp_path = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    ordered_names = []
    if HOME_XML_ENTRY in entries:
        ordered_names.append(HOME_XML_ENTRY)
    ordered_names.extend(sorted(name for name in entries if name != HOME_XML_ENTRY))

    try:
        with zipfile.ZipFile(tmp_path, "w", compression=compression) as archive:
            for name in ordered_names:
                info = zipfile.ZipInfo(filename=name, date_time=ZIP_EPOCH)
                info.compress_type = compression
                archive.writestr(info, entries[name])
        os.replace(tmp_path, path)
        return path.stat().st_size
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
