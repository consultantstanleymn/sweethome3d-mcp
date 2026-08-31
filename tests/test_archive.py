from pathlib import Path
import zipfile

import pytest

from sh3d_mcp.sh3d.archive import read_entries, write_sh3d
from sh3d_mcp.sh3d.constants import HOME_XML_ENTRY


def test_write_sh3d_and_read_entries_round_trip_three_entries(tmp_path: Path) -> None:
    project_path = tmp_path / "roundtrip.sh3d"
    entries = {
        HOME_XML_ENTRY: b"<?xml version='1.0'?><home/>",
        "textures/a.png": b"texture-bytes",
        "models/1.obj": b"model-bytes",
    }

    bytes_written = write_sh3d(project_path, entries)

    assert bytes_written == project_path.stat().st_size
    assert read_entries(project_path) == entries


def test_write_sh3d_failure_leaves_original_file_untouched_and_cleans_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_path = tmp_path / "atomic.sh3d"
    original_bytes = b"original-bytes"
    project_path.write_bytes(original_bytes)

    entries = {
        HOME_XML_ENTRY: b"<?xml version='1.0'?><home/>",
        "models/1.obj": b"first",
        "textures/a.png": b"second",
    }

    original_writestr = zipfile.ZipFile.writestr
    call_count = {"value": 0}

    def failing_writestr(self: zipfile.ZipFile, zinfo_or_arcname, data, *args, **kwargs):
        call_count["value"] += 1
        original_writestr(self, zinfo_or_arcname, data, *args, **kwargs)
        if call_count["value"] == 2:
            raise RuntimeError("simulated write failure")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", failing_writestr)

    with pytest.raises(RuntimeError, match="simulated write failure"):
        write_sh3d(project_path, entries)

    assert project_path.read_bytes() == original_bytes
    assert list(tmp_path.glob("atomic.sh3d.tmp-*")) == []
