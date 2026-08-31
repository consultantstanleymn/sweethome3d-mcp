"""Nominal, unverified furniture catalogue data.

The built-in dimensions in this module are convenience defaults only. Per
`docs/SCHEMA.md §9-E`, model-less furniture behavior in Sweet Home 3D 3D view is
still unverified, and these dimensions are not schema facts. Treat them as
nominal placeholders until validated against real Sweet Home 3D-authored files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from sh3d_mcp.sh3d.document import Sh3dDocument


@dataclass(frozen=True)
class CatalogEntry:
    """Resolved furniture catalogue entry."""

    catalog_id: str
    name: str
    width: float
    depth: float
    height: float
    model_rotation: str = "1 0 0 0 1 0 0 0 1"
    model_bytes: bytes | None = None
    model_entry_name: str | None = None


BUILTIN_CATALOG: dict[str, CatalogEntry] = {
    "eTeks#armchair": CatalogEntry("eTeks#armchair", "Armchair", 90.0, 90.0, 85.0),
    "eTeks#bath": CatalogEntry("eTeks#bath", "Bath", 170.0, 75.0, 60.0),
    "eTeks#bed": CatalogEntry("eTeks#bed", "Bed", 140.0, 200.0, 55.0),
    "eTeks#bookcase": CatalogEntry("eTeks#bookcase", "Bookcase", 90.0, 30.0, 200.0),
    "eTeks#chair": CatalogEntry("eTeks#chair", "Chair", 45.0, 45.0, 90.0),
    "eTeks#coffeeTable": CatalogEntry("eTeks#coffeeTable", "Coffee table", 120.0, 60.0, 45.0),
    "eTeks#cornerSofa": CatalogEntry("eTeks#cornerSofa", "Corner sofa", 220.0, 160.0, 85.0),
    "eTeks#desk": CatalogEntry("eTeks#desk", "Desk", 140.0, 70.0, 75.0),
    "eTeks#dishwasher": CatalogEntry("eTeks#dishwasher", "Dishwasher", 60.0, 60.0, 85.0),
    "eTeks#doubleBed": CatalogEntry("eTeks#doubleBed", "Double bed", 160.0, 200.0, 55.0),
    "eTeks#doubleDoorCabinet": CatalogEntry("eTeks#doubleDoorCabinet", "Double-door cabinet", 100.0, 40.0, 200.0),
    "eTeks#dresser": CatalogEntry("eTeks#dresser", "Dresser", 120.0, 50.0, 90.0),
    "eTeks#fridge": CatalogEntry("eTeks#fridge", "Fridge", 70.0, 70.0, 185.0),
    "eTeks#kitchenBaseCabinet": CatalogEntry("eTeks#kitchenBaseCabinet", "Kitchen base cabinet", 60.0, 60.0, 85.0),
    "eTeks#kitchenCorner": CatalogEntry("eTeks#kitchenCorner", "Kitchen corner cabinet", 90.0, 90.0, 85.0),
    "eTeks#kitchenSinkCabinet": CatalogEntry("eTeks#kitchenSinkCabinet", "Kitchen sink cabinet", 80.0, 60.0, 85.0),
    "eTeks#kitchenWallCabinet": CatalogEntry("eTeks#kitchenWallCabinet", "Kitchen wall cabinet", 60.0, 35.0, 70.0),
    "eTeks#nightstand": CatalogEntry("eTeks#nightstand", "Nightstand", 45.0, 40.0, 50.0),
    "eTeks#oven": CatalogEntry("eTeks#oven", "Oven", 60.0, 60.0, 60.0),
    "eTeks#roundTable": CatalogEntry("eTeks#roundTable", "Round table", 120.0, 120.0, 75.0),
    "eTeks#shower": CatalogEntry("eTeks#shower", "Shower", 90.0, 90.0, 210.0),
    "eTeks#singleBed": CatalogEntry("eTeks#singleBed", "Single bed", 90.0, 200.0, 55.0),
    "eTeks#sink": CatalogEntry("eTeks#sink", "Sink", 60.0, 50.0, 20.0),
    "eTeks#sofa": CatalogEntry("eTeks#sofa", "Sofa", 200.0, 90.0, 85.0),
    "eTeks#squareTable": CatalogEntry("eTeks#squareTable", "Square table", 90.0, 90.0, 75.0),
    "eTeks#stool": CatalogEntry("eTeks#stool", "Stool", 35.0, 35.0, 45.0),
    "eTeks#table": CatalogEntry("eTeks#table", "Table", 160.0, 90.0, 75.0),
    "eTeks#toilet": CatalogEntry("eTeks#toilet", "Toilet", 40.0, 70.0, 80.0),
    "eTeks#tvStand": CatalogEntry("eTeks#tvStand", "TV stand", 140.0, 45.0, 55.0),
    "eTeks#wardrobe": CatalogEntry("eTeks#wardrobe", "Wardrobe", 180.0, 60.0, 220.0),
    "eTeks#washingMachine": CatalogEntry("eTeks#washingMachine", "Washing machine", 60.0, 60.0, 85.0),
}


_REFERENCE_CACHE: dict[tuple[str, float], "ReferenceCatalog"] = {}


class ReferenceCatalog:
    """Reference-derived catalogue entries indexed from a real .sh3d file."""

    _DEFAULT_MODEL_ROTATION: ClassVar[str] = "1 0 0 0 1 0 0 0 1"

    def __init__(self, source_path: Path, entries: dict[str, CatalogEntry]) -> None:
        self.source_path = source_path
        self.entries = entries

    @classmethod
    def from_project_path(cls, project_path: str | Path) -> "ReferenceCatalog":
        """Build or reuse a cached reference catalogue from a .sh3d file."""

        path = Path(project_path).expanduser().resolve()
        cache_key = (str(path), path.stat().st_mtime)
        cached = _REFERENCE_CACHE.get(cache_key)
        if cached is not None:
            return cached

        document = Sh3dDocument.open(path)
        entries: dict[str, CatalogEntry] = {}
        for piece in document.root.iter("pieceOfFurniture"):
            catalog_id = piece.attrib.get("catalogId")
            if not catalog_id:
                continue
            model_entry_name = piece.attrib.get("model")
            model_bytes = document.entries.get(model_entry_name) if model_entry_name is not None else None
            entries[catalog_id] = CatalogEntry(
                catalog_id=catalog_id,
                name=piece.attrib["name"],
                width=float(piece.attrib["width"]),
                depth=float(piece.attrib["depth"]),
                height=float(piece.attrib["height"]),
                model_rotation=piece.attrib.get("modelRotation", cls._DEFAULT_MODEL_ROTATION),
                model_bytes=model_bytes,
                model_entry_name=model_entry_name,
            )

        catalog = cls(path, entries)
        _REFERENCE_CACHE[cache_key] = catalog
        return catalog

    def get(self, catalog_id: str) -> CatalogEntry | None:
        """Return one indexed reference entry by catalog id."""

        return self.entries.get(catalog_id)


def resolve_catalog_entry(
    catalog_id: str,
    reference_catalog: ReferenceCatalog | None = None,
) -> CatalogEntry | None:
    """Resolve a catalogue id by preferring a reference catalogue over the built-in table."""

    if reference_catalog is not None:
        entry = reference_catalog.get(catalog_id)
        if entry is not None:
            return entry
    return BUILTIN_CATALOG.get(catalog_id)
