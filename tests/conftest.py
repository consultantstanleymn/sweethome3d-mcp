import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from sh3d_mcp.tools.project import create_project


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file for atomic-write assertions."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create and return a fresh empty .sh3d project under pytest's tmp_path."""

    project_path = tmp_path / "project.sh3d"
    create_project(project_path=str(project_path), name="House")
    return project_path


@pytest.fixture
def hand_built_home_xml():
    """Build a raw Home.xml root element for edge-case archive fixtures."""

    def _build(
        *,
        name: str = "Fixture",
        version: str = "5300",
        wall_height: str = "250",
        attrs: dict[str, str] | None = None,
        children: list[ET.Element] | None = None,
    ) -> ET.Element:
        root_attrs = {
            "version": version,
            "name": name,
            "camera": "topCamera",
            "wallHeight": wall_height,
        }
        if attrs is not None:
            root_attrs.update(attrs)
        root = ET.Element("home", root_attrs)
        for child in children or []:
            root.append(child)
        return root

    return _build
