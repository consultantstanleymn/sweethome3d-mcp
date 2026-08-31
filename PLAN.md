# Implementation Plan — Phases 2–4

Read `docs/SCHEMA.md`, `docs/ARCHITECTURE.md`, `docs/TOOL_INTERFACE.md`, `docs/VALIDATION.md`
first. Every item below is written to be handed to a fresh implementer with **no other
context**: it names the target module, the exact signature, the exact XML it must emit, the
validation sections it must call, and the test it must write.

Conventions binding on all items:
- Python 3.10+, stdlib only except `mcp`. No `lxml`, `numpy`, or `pydantic`.
- Lengths in **cm**; angles in **degrees at the tool boundary, radians in XML**.
- Never `print()` — stdio is the MCP channel (ARCHITECTURE.md §9).
- `tools/*.py` must contain no XML literals and no `zipfile` calls.
- Every public function gets a docstring per TOOL_INTERFACE.md §13.

---

## Phase 2 — Scaffolding and core ZIP/XML I/O

**2.1 Repository scaffolding.**
Create the tree in ARCHITECTURE.md §8 (empty `__init__.py` in every package). Write
`pyproject.toml`: `[project] name="sweethome3d-mcp"`, `requires-python=">=3.10"`,
`dependencies=["mcp"]`, `[project.optional-dependencies] dev=["pytest"]`,
`[project.scripts] sweethome3d-mcp="sh3d_mcp.server:main"`, and a `src/` layout
`[tool.setuptools] package-dir={""="src"}`. Add `.gitignore` (`__pycache__/`, `*.egg-info/`,
`.pytest_cache/`, `dist/`, `*.sh3d` under `tests/tmp/`).
*Done when:* `pip install -e .[dev]` succeeds and `python -c "import sh3d_mcp"` works.

**2.2 `errors.py`.**
`class ErrorCode(str, Enum)` with exactly the 21 codes in TOOL_INTERFACE.md §2.
`class Sh3dError(Exception)` with `__init__(self, code: ErrorCode, message: str,
details: dict | None = None, hint: str | None = None)` and
`.to_dict() -> dict` producing the `{"ok": false, "error": {...}}` envelope verbatim.
*Test:* envelope shape matches the documented JSON key-for-key.

**2.3 `sh3d/constants.py`.**
`CURRENT_VERSION = "5300"` (SCHEMA.md §9-C); `DEFAULT_WALL_HEIGHT = 250.0`;
`DEFAULT_WALL_THICKNESS = 7.5`; `DEFAULT_FLOOR_THICKNESS = 12.0`;
`HOME_XML_ENTRY = "Home.xml"`; `LEGACY_HOME_ENTRY = "Home"`;
`CONTENT_DIGESTS_ENTRY = "ContentDigests"`;
`HOME_CHILD_ORDER: tuple[str, ...]` = the 14 tags in DTD sequence (SCHEMA.md §5.1);
`ROOM_CHILD_ORDER = ("property","textStyle","texture","point")`;
`KNOWN_TAGS: frozenset[str]` and `KNOWN_ATTRS: dict[str, frozenset[str]]` transcribed from
the DTD in SCHEMA.md §5 (used by 4.4 and by `open_reference`).
*Test:* `HOME_CHILD_ORDER` has no duplicates and contains `wall`, `room`, `dimensionLine`.

**2.4 `sh3d/archive.py` — ZIP layer.**
```python
def read_entries(path: Path) -> dict[str, bytes]
def write_sh3d(path: Path, entries: dict[str, bytes], compress: bool = True) -> int
```
`read_entries` raises `Sh3dError(NOT_A_ZIP)` on `zipfile.BadZipFile` and
`Sh3dError(PROJECT_NOT_FOUND)` if missing. `write_sh3d` writes `Home.xml` **first**, then
remaining entries sorted by name, using `ZIP_DEFLATED` (or `ZIP_STORED` if `compress=False`);
it writes to `path.with_suffix(path.suffix + f".tmp-{os.getpid()}")` and `os.replace()`s
(ARCHITECTURE.md §4.1). Returns bytes written.
*Test:* round-trip a dict of 3 entries; assert an interrupted write (raise inside the
`with`) leaves the original file untouched.

**2.5 `sh3d/document.py` — `Sh3dDocument`.**
```python
class Sh3dDocument:
    root: ET.Element                 # the <home> element
    entries: dict[str, bytes]        # every non-Home.xml entry, verbatim
    path: Path
    @classmethod
    def create(cls, path, name, wall_height=250.0) -> "Sh3dDocument"
    @classmethod
    def open(cls, path: Path) -> "Sh3dDocument"
    def save(self, destination: Path | None = None) -> int
```
`open` reads entries, requires `Home.xml` (else `MISSING_HOME_XML` — say explicitly in the
message that a legacy `Home`-only file must be re-saved by Sweet Home 3D 6+ first), parses
with `ET.fromstring` (else `MALFORMED_XML`), and stores all other entries **except**
`Home` and `ContentDigests`, which are dropped (ARCHITECTURE.md §3).
`create` builds `<home version='5300' name=... camera='topCamera' wallHeight=...>`.
`save` calls `reorder_children` then serialises with
`ET.tostring(root, encoding="utf-8", xml_declaration=True)` and calls `write_sh3d`.
*Test:* create → save → open → assert `@name` survives.

**2.6 Child reordering.**
`document.reorder_children(root)`: stable sort of `<home>`'s children by
`HOME_CHILD_ORDER.index(tag)`, unknown tags ranked last with original relative order
preserved; recursively applies `ROOM_CHILD_ORDER` to each `<room>`.
Use `list(root)` + `root[:] = sorted(...)`; `sorted` is stable, so this is safe.
*Test:* build a `<home>` with children in reverse DTD order plus one `<weirdTag/>`; assert
output order is DTD order with `weirdTag` last.

**2.7 Round-trip preservation (the correctness backbone).**
`document.py` must not drop anything. Write `tests/test_roundtrip.py`: hand-build a
`Home.xml` containing `<environment>`, `<observerCamera>`, `<compass>`, a `<wall>` with a
`<baseboard>` child and a `topColor` attribute, a `<polyline>`, and a `<label><text>Hi</text></label>`;
zip it with a dummy `"models/1.obj"` entry; `open` → `save` → `open`; assert **every**
element and attribute is still present and `entries["models/1.obj"]` is byte-identical.
*This test gates all of Phase 3 — do not proceed until it passes.*

**2.8 `sh3d/document.py::IdAllocator`.**
Scans every `id` attribute in the document at load. `next_id(prefix: str) -> str` returns
`f"{prefix}{n}"` for the smallest `n ≥ 0` not already used with that prefix, and records it
so it is never reissued during the document's lifetime (ARCHITECTURE.md §6).
*Test:* a document with `wall0`, `wall2` yields `wall1` then `wall3`.

**2.9 `geometry/primitives.py`.**
`Pt = tuple[float,float]`; `almost_equal`, `dist`, `orient(a,b,c)`,
`segments_properly_intersect`, `segments_collinear_overlap`, `shoelace_signed_area`,
`polygon_bbox`, `point_in_polygon` (half-open rule + explicit on-boundary result),
`oriented_rect_corners(x,y,w,d,angle_rad)`, `sat_overlap(rect_a, rect_b)`.
All tolerances from VALIDATION.md §1 defined here as module constants.
*Test:* a table-driven suite per function, including the collinear, shared-vertex, and
full-containment cases named in VALIDATION.md §4.4/§4.6.

**2.10 `geometry/validation.py`.**
`check_scalars(**kwargs)` implementing VALIDATION.md §2 (with the explicit
`math.isfinite` guard — `NaN` must not slip through), `validate_room_points` (§4.1–4.5,
returns cleaned points + warnings), `rooms_overlap` (§4.6), `wall_is_duplicate` (§5.1),
`walls_properly_cross` (§5.2), `furniture_overlaps` (§6).
Each raises `Sh3dError` with the documented code, or returns a `(bool, details)` pair where
the caller decides error-vs-warning.
*Test:* one test per numbered rule in VALIDATION.md, asserting the exact `ErrorCode`.

**2.11 `server.py` skeleton.**
`FastMCP("sweethome3d")` instance, `logging.basicConfig(stream=sys.stderr)`, a
`@tool_wrapper` decorator that catches `Sh3dError → .to_dict()` and any other `Exception →
Sh3dError(IO_ERROR, str(e)).to_dict()`, and `def main(): mcp.run()`. `__main__.py` calls it.
Register **one** trivial tool (`ping`) to prove the transport.
*Done when:* `python -m sh3d_mcp` starts and an MCP client lists `ping`.

---

## Phase 3 — Per-tool implementation

Each item is independently implementable. All of them: open with `Sh3dDocument.open`,
validate in the VALIDATION.md §7 order, mutate, `doc.save()`, return the documented dict.
**No partial writes** — nothing touches disk unless all validation passed.

**3.1 `sh3d/elements.py` — element factories.** *(prerequisite for 3.2–3.6; do this first)*
```python
def make_wall(id, x1, y1, x2, y2, thickness, height=None, height_at_end=None, level=None) -> ET.Element
def make_room(id, points: list[Pt], name=None, area_visible=True, level=None) -> ET.Element
def make_furniture(id, catalog_id, name, x, y, angle_rad, width, depth, height,
                   elevation=0.0, model_entry=None, level=None) -> ET.Element
def make_dimension_line(id, x1, y1, x2, y2, offset, angle_rad=0.0, visible_in_3d=False) -> ET.Element
def fmt(v: float) -> str        # trimmed float formatting, SCHEMA.md §9-I
def wall_view(el) -> WallView   # + room_view, furniture_view, dimension_view
```
Emit **only** attributes listed in the DTD for that element (SCHEMA.md §5); omit any
attribute whose value equals the DTD default; **never** emit a `model`/`icon` attribute
unless the corresponding ZIP entry is being written (SCHEMA.md §5.6). `make_room` appends
one `<point x= y=>` child per point, **without** repeating the first point.
*Test:* `make_wall` output has exactly `{id,xStart,yStart,xEnd,yEnd,thickness}` when height
is `None`; every emitted attribute name is in `KNOWN_ATTRS[tag]`.

**3.2 `create_project`** → `tools/project.py::create_project`.
Signature and full semantics in TOOL_INTERFACE.md §3 (including the **exterior-dimension**
rectangle interpretation and the inner-face room). Uses `Sh3dDocument.create`,
`make_wall` ×4, `make_room` ×1, and sets all eight join IDREFs explicitly per
VALIDATION.md §3.3. Rejects `overwrite=False` on an existing path with `PROJECT_EXISTS`.
*Test:* `create_project(w=800,h=600,t=7.5)` produces 4 walls whose centrelines are at
`3.75`/`796.25`/`3.75`/`596.25`, a room of area `(800-15)*(600-15) cm²`, and 8 consistent
reciprocal IDREFs. Also: opening the produced file with `Sh3dDocument.open` works.

**3.3 `add_wall`** → `tools/walls.py::add_wall`.
Signature and rules in TOOL_INTERFACE.md §4. Order: `check_scalars` (§2) →
`wall_is_duplicate` (§5.1) → `walls_properly_cross` (§5.2, error unless `allow_crossing`) →
`make_wall` with `IdAllocator.next_id("wall")` → `joins.join_new_wall` if `join=True` → save.
*Test:* two walls sharing a corner within 2 cm get reciprocal IDREFs and the second wall's
endpoint is snapped exactly onto the first's; re-adding an identical wall returns
`WALL_DUPLICATE` and leaves the file's SHA-256 unchanged.

**3.4 `geometry/joins.py::join_new_wall`** — VALIDATION.md §3.2, all six steps including the
occupied-end skip, deterministic tie-break by wall id, reciprocal write, endpoint snap, and
the T-junction warning text from §3.1.
*Test:* three wall ends meeting at one point ⇒ exactly one reciprocal pair, and the third
call returns the documented T-junction warning.

**3.5 `add_room`** → `tools/rooms.py::add_room`.
Signature in TOOL_INTERFACE.md §5. Calls `validate_room_points` (VALIDATION.md §4.1–4.5,
which returns cleaned points + the "dropped repeated closing point" warning), then
`rooms_overlap` against every existing room (§4.6) unless `allow_overlap`. Writes with
`make_room`, reports `area_cm2` and `area_m2`.
*Test:* a duplicated closing point is dropped with the documented warning; a bowtie returns
`ROOM_SELF_INTERSECTS`; two edge-sharing rectangles do **not** report overlap; a rectangle
fully inside another **does**.

**3.6 `add_furniture`** → `tools/furniture.py::add_furniture`.
Signature in TOOL_INTERFACE.md §6. Implements the three-tier dimension resolution of
ARCHITECTURE.md §7 in that exact precedence, `math.radians(rotation % 360)` conversion, the
`room_name` **placement assertion** (point-in-polygon; `ELEMENT_NOT_FOUND`/`AMBIGUOUS_NAME`/
`INVALID_ARGUMENT` with the room bbox in details), model-byte copying into the target ZIP
under a fresh entry name, and the "no 3D model" warning when none is available.
*Test:* an unknown id with no explicit dims returns `UNKNOWN_CATALOG_ID` listing available
ids; a built-in id emits no `model` attribute; `room_name` pointing at a room that does not
contain `(x,y)` is rejected.

**3.7 `catalog.py`.**
`BUILTIN_CATALOG: dict[str, CatalogEntry]` — ~30 eTeks default ids with name and nominal
`width/depth/height` in cm, `model=None`. **Mark the whole table as nominal/unverified in a
module docstring**; these dimensions are conveniences, not schema facts.
`class ReferenceCatalog` — built by `open_reference` from a real `.sh3d`, mapping
`catalogId → (name, w, d, h, modelRotation, model_bytes, model_entry_name)`; module-level
cache keyed by `(abspath, mtime)`.
*Test:* a reference file's pieces are indexed and take precedence over the built-in table.

**3.8 `add_dimension`** → `tools/dimensions.py::add_dimension`.
TOOL_INTERFACE.md §7. `offset` is `#REQUIRED` — always emit it, defaulting to `20.0`.
Length ≥ `MIN_DIMENSION_LENGTH`.
*Test:* a zero-length dimension returns `DEGENERATE_DIMENSION`; the emitted element has
`xStart,yStart,xEnd,yEnd,offset` and an `id`.

**3.9 `list_elements`** → `tools/inspect.py::list_elements`.
TOOL_INTERFACE.md §8. Read-only — must not call `save`. Builds the `*View` dataclasses,
computes `bounds` over all wall endpoints and room points, resolves each piece's
`room_name` by point-in-polygon, and populates `unsupported_elements_present` from tags
present but not in our editable set.
*Test:* on the Phase-2.7 round-trip fixture, `unsupported_elements_present` contains
`environment` and `observerCamera`, and the file's mtime is unchanged.

**3.10 `export_project`** → `tools/project.py::export_project`.
TOOL_INTERFACE.md §9 — the "finalise, verify and report" semantics. Runs the full
validation pass, re-serialises in canonical order, optionally writes to
`destination_path`, and returns entries + counts + the `note` about dropped legacy entries.
Any other output format ⇒ `UNSUPPORTED_FEATURE`.
*Test:* export is idempotent — exporting twice yields byte-identical output.

**3.11 `open_reference`** → `tools/inspect.py::open_reference`.
TOOL_INTERFACE.md §10. Never writes to the sample. Produces the entry listing, `home`
attributes, tag census, `unknown_tags`/`unknown_attributes` (diffed against
`constants.KNOWN_TAGS`/`KNOWN_ATTRS`), and populates the `ReferenceCatalog`.
A legacy `Home`-only file ⇒ `MISSING_HOME_XML` with the explicit remediation message.
*Test:* on a synthetic file containing `<futureThing/>`, `unknown_tags == ["futureThing"]`.

**3.12 `validate_project`** → `tools/project.py::validate_project`.
TOOL_INTERFACE.md §11. Runs every VALIDATION.md rule over an existing document, including
the §3.4 join-integrity checks (dangling IDREF, non-reciprocal, distant endpoints). Never
mutates.
*Test:* a hand-built file with a dangling `wallAtStart` reports `ELEMENT_NOT_FOUND`.

**3.13 `delete_element`** → `tools/inspect.py::delete_element`.
TOOL_INTERFACE.md §12. Must clear every inbound `wallAtStart`/`wallAtEnd` IDREF when
deleting a wall — a dangling IDREF corrupts the file.
*Test:* deleting a joined wall clears the neighbour's reference and
`validate_project` then reports no errors.

**3.14 Register all tools in `server.py`.**
One `@mcp.tool()` wrapper per item 3.2–3.13, each with a full type-annotated signature and a
docstring meeting TOOL_INTERFACE.md §13 (cm/degrees/`y`-down/limits/example). Wrappers
contain no logic beyond delegation and error-envelope conversion.
*Test:* an in-process MCP client lists exactly the expected tool names and each tool's
generated JSON Schema has the expected required parameters.

---

## Phase 4 — Tests, docs, and schema cross-checks

**4.1 Test fixtures.** `tests/conftest.py`: a `tmp_project` fixture producing a fresh
`.sh3d` under `tmp_path`; a `hand_built_home_xml` helper; a `sha256(path)` helper for the
no-partial-write assertions.

**4.2 Failure atomicity suite.** For **every** mutating tool, assert that a call which fails
validation leaves the target file's SHA-256 unchanged (VALIDATION.md §7).

**4.3 Golden-file test.** Commit the minimal document from SCHEMA.md §7 as
`tests/data/minimal_home.xml`; assert our writer's output parses to an equivalent tree
(element/attribute set equality — **not** byte equality, per ARCHITECTURE.md §2.1).

**4.4 DTD conformance test** (`tests/test_schema_conformance.py`). Walk every element our
code can emit; assert `tag ∈ KNOWN_TAGS` and `set(el.attrib) ⊆ KNOWN_ATTRS[tag]`. This is
the guard against inventing attributes Sweet Home 3D will ignore or choke on.

**4.5 Round-trip fuzz.** Generate N random valid homes (random wall/room/furniture counts),
save → open → save, assert the second save is byte-identical to the first (idempotence) and
that element counts are preserved.

**4.6 RESOLVE SCHEMA.md §9-B — axis and angle sign.** Obtain a real `.sh3d` authored by
Sweet Home 3D containing one rectangular room and one piece of furniture rotated 90°.
Inspect it with `open_reference`; confirm (a) `y` increases downward, (b) the sign of a
90°-clockwise rotation in radians, (c) that our shoelace winding matches. **Update
docs/SCHEMA.md §4 and §9-B with the verified answer and remove the uncertainty flag.**
Until this is done, every rotation-related docstring must retain the "(unverified)" note.

**4.7 RESOLVE SCHEMA.md §9-E — model-less furniture.** Open a generated file containing a
model-less `pieceOfFurniture` in a real Sweet Home 3D 7.x and record whether the 3-D view
renders a placeholder, renders nothing, or errors. Update SCHEMA.md §9-E and, if the answer
is "errors", change ARCHITECTURE.md §7 tier 2/3 to refuse model-less pieces.

**4.8 RESOLVE SCHEMA.md §9-A — XML-only compatibility floor.** Open a generated XML-only
`.sh3d` in a real Sweet Home 3D 7.x and confirm it loads with walls, rooms and furniture
intact. Record the tested version in SCHEMA.md and README. **This is the single
highest-risk assumption in the project** — if it fails, the whole approach needs a rethink
and every later phase depends on it, so run it as early in Phase 4 as a real install can be
obtained.

**4.9 `no print()` guard.** A test that greps `src/` for `\bprint\(` and fails — stdout is
the MCP transport (ARCHITECTURE.md §9).

**4.10 Docstring audit.** Assert every registered tool's docstring is non-empty, mentions
"centimet", and (for tools taking a rotation) mentions "degree".

**4.11 README.md.** What it is; install (`pip install -e .`); the client registration JSON
from ARCHITECTURE.md §9; a worked example (create a 8×6 m home, add an interior wall, two
rooms, a table, a dimension line, export); the explicit limitations list (single level; no
doors/windows/lights/textures; no rendering; no live sync; `.sh3d` output only); a
"Verified against Sweet Home 3D version X" line filled in by 4.8; and the GPL/attribution
note that the schema was derived from Sweet Home 3D's GPL source and published DTD.

**4.12 Docs cross-check pass.** Re-read all four `docs/` files against the finished code and
fix every drift. Specifically: the error-code table in TOOL_INTERFACE.md §2 must exactly
equal `ErrorCode`'s members (assert this in a test), and every tolerance named in
VALIDATION.md §1 must exist in `geometry/primitives.py` with that value (assert this too).
Move every §9 item that 4.6–4.8 resolved out of "Open questions" and into the body.

---

## Prior art worth checking before Phase 2

- `github.com/grimashevich/sweethome3d-mcp-server`
- `github.com/rostskadat/FreeCAD-SH3D` (a Python `.sh3d` parser)

## Biggest open uncertainties (see docs/SCHEMA.md §9 for full detail)

1. **§9-A / item 4.8 — highest risk.** XML-only files *should* load per source analysis, but
   this was never tested against a real Sweet Home 3D install. Run this first in Phase 4.
2. **§9-B / item 4.6.** The `y`-down axis and clockwise sense of positive `angle` are
   inferred, not confirmed.
3. **§9-E / item 4.7.** Whether model-less furniture renders acceptably in 3-D.
4. **§9-C.** Current `Home.CURRENT_VERSION` unknown (5300 is from a 2017 mirror); mitigated
   by deliberately writing the lower value.
5. **§9-D.** Colour attribute encoding unread — deferred by emitting no colours in v1.
