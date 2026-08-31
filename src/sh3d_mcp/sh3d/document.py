"""Document-level open/create/save helpers for Sweet Home 3D .sh3d files."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from sh3d_mcp.errors import ErrorCode, Sh3dError

from . import archive
from .constants import (
    CONTENT_DIGESTS_ENTRY,
    CURRENT_VERSION,
    HOME_CHILD_ORDER,
    HOME_XML_ENTRY,
    LEGACY_HOME_ENTRY,
    ROOM_CHILD_ORDER,
)


def reorder_children(root: ET.Element) -> None:
    """Reorder home and room children into canonical DTD order, preserving unknown-tag order."""

    home_order = {tag: index for index, tag in enumerate(HOME_CHILD_ORDER)}
    room_order = {tag: index for index, tag in enumerate(ROOM_CHILD_ORDER)}

    home_children = list(root)
    root[:] = sorted(
        home_children,
        key=lambda child: home_order.get(child.tag, len(home_order)),
    )

    for room in root.iter("room"):
        room_children = list(room)
        room[:] = sorted(
            room_children,
            key=lambda child: room_order.get(child.tag, len(room_order)),
        )


class IdAllocator:
    """Allocate stable per-prefix ids without reusing values during a document lifetime."""

    def __init__(self, root: ET.Element) -> None:
        self._used_ids = {
            element_id
            for element in root.iter()
            if (element_id := element.get("id")) is not None
        }

    def next_id(self, prefix: str) -> str:
        """Return the smallest unused id for a prefix and reserve it immediately."""

        index = 0
        while True:
            candidate = f"{prefix}{index}"
            if candidate not in self._used_ids:
                self._used_ids.add(candidate)
                return candidate
            index += 1


class Sh3dDocument:
    """In-memory representation of a Sweet Home 3D Home.xml tree plus non-XML ZIP entries."""

    def __init__(self, root: ET.Element, entries: dict[str, bytes], path: Path) -> None:
        self.root = root
        self.entries = entries
        self.path = path
        self.id_allocator = IdAllocator(root)

    @classmethod
    def create(
        cls,
        path: Path,
        name: str,
        wall_height: float = 250.0,
    ) -> "Sh3dDocument":
        """Create a new in-memory document with the minimal root home element."""

        root = ET.Element(
            "home",
            {
                "version": CURRENT_VERSION,
                "name": name,
                "camera": "topCamera",
                "wallHeight": str(wall_height),
            },
        )
        return cls(root=root, entries={}, path=Path(path))

    @classmethod
    def open(cls, path: Path) -> "Sh3dDocument":
        """Open a .sh3d archive, requiring Home.xml and dropping legacy write-only entries."""

        archive_path = Path(path)
        entries = archive.read_entries(archive_path)
        home_xml = entries.get(HOME_XML_ENTRY)
        if home_xml is None:
            raise Sh3dError(
                ErrorCode.MISSING_HOME_XML,
                (
                    f'ZIP archive is missing "{HOME_XML_ENTRY}". '
                    "A legacy Home-only file must be re-saved by Sweet Home 3D 6+ first."
                ),
            )

        try:
            root = ET.fromstring(home_xml)
        except ET.ParseError as exc:
            raise Sh3dError(
                ErrorCode.MALFORMED_XML,
                f'Failed to parse "{HOME_XML_ENTRY}": {exc}',
            ) from exc

        other_entries = {
            name: data
            for name, data in entries.items()
            if name not in {HOME_XML_ENTRY, LEGACY_HOME_ENTRY, CONTENT_DIGESTS_ENTRY}
        }
        return cls(root=root, entries=other_entries, path=archive_path)

    def save(self, destination: Path | None = None) -> int:
        """Serialize Home.xml and write the archive atomically."""

        reorder_children(self.root)
        target_path = self.path if destination is None else Path(destination)
        serialized_home = ET.tostring(self.root, encoding="utf-8", xml_declaration=True)
        entries = {HOME_XML_ENTRY: serialized_home, **self.entries}
        return archive.write_sh3d(target_path, entries)
