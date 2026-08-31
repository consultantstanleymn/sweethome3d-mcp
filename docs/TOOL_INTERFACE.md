# MCP Tool Interface

All lengths are **centimetres**, all angles at the tool boundary are **degrees**
(converted to radians on write — SCHEMA.md §4). Coordinates are floats in the plan plane,
`x` right, `y` down.

## 1. Common types

```python
Point = tuple[float, float]          # (x, y) in cm

@dataclass(frozen=True)
class WallView:
    id: str; x_start: float; y_start: float; x_end: float; y_end: float
    thickness: float; height: float | None; length: float
    wall_at_start: str | None; wall_at_end: str | None

@dataclass(frozen=True)
class RoomView:
    id: str; name: str | None; points: list[Point]
    area_cm2: float; is_convex: bool

@dataclass(frozen=True)
class FurnitureView:
    id: str; catalog_id: str | None; name: str
    x: float; y: float; angle_degrees: float
    width: float; depth: float; height: float; elevation: float
    has_model: bool; room_name: str | None      # room_name resolved by point-in-polygon

@dataclass(frozen=True)
class DimensionView:
    id: str; x_start: float; y_start: float; x_end: float; y_end: float
    offset: float; length: float
```

Every tool returns a `dict`. Success envelope always contains `"ok": true`.

## 2. Error envelope and taxonomy

Failures are **returned**, not raised — an MCP tool that raises gives the model an opaque
string. Every failure returns:

```json
{ "ok": false,
  "error": { "code": "ROOM_NOT_CLOSED",
             "message": "Room polygon has only 2 points; at least 3 are required.",
             "details": { "point_count": 2 },
             "hint": "Pass at least 3 distinct points; do not repeat the first point." } }
```

`ErrorCode` (in `errors.py`) — the complete set:

| Code | Meaning |
|---|---|
| `BAD_PATH` | path missing `.sh3d` suffix, or points at a directory |
| `PROJECT_NOT_FOUND` | `project_path` does not exist |
| `PROJECT_EXISTS` | `create_project` target exists and `overwrite=False` |
| `NOT_A_ZIP` | file is not a readable ZIP archive |
| `MISSING_HOME_XML` | ZIP has no `Home.xml` entry (legacy `Home`-only file) |
| `MALFORMED_XML` | `Home.xml` fails to parse |
| `INVALID_ARGUMENT` | type/range failure not covered by a specific code |
| `DEGENERATE_DIMENSION` | zero/negative/NaN length, thickness, height, width or depth |
| `WALL_TOO_SHORT` | wall length below `MIN_WALL_LENGTH` |
| `WALL_DUPLICATE` | a collinear-overlapping wall already exists |
| `WALL_CROSSES_WALL` | new wall properly crosses an existing wall mid-span |
| `ROOM_TOO_FEW_POINTS` | fewer than 3 distinct points |
| `ROOM_DEGENERATE` | shoelace area below `MIN_ROOM_AREA` |
| `ROOM_SELF_INTERSECTS` | non-simple polygon |
| `ROOM_OVERLAPS` | overlaps an existing room beyond tolerance |
| `FURNITURE_OVERLAPS` | footprint overlaps existing furniture (warning-by-default) |
| `UNKNOWN_CATALOG_ID` | id not in reference catalogue, built-in table, or explicit dims |
| `ELEMENT_NOT_FOUND` | id given to `delete_element` / `room_name` does not resolve |
| `AMBIGUOUS_NAME` | `room_name` matches more than one room |
| `UNSUPPORTED_FEATURE` | multi-level, doors/windows, textures, rendering |
| `IO_ERROR` | anything from the filesystem |

### 2.1 Universal input validation (applied by every tool before anything else)
1. Every numeric argument must be finite: reject `NaN`/`±inf` → `INVALID_ARGUMENT`.
2. Every coordinate must satisfy `|v| <= 1_000_000` (10 km) → `INVALID_ARGUMENT`.
3. `project_path` per ARCHITECTURE.md §10 → `BAD_PATH`.
4. Booleans are real booleans; strings `"true"`/`"false"` are accepted and coerced (LLM
   clients emit these), anything else → `INVALID_ARGUMENT`.

## 3. `create_project`

```python
def create_project(
    project_path: str,
    name: str,
    width: float | None = None,
    height: float | None = None,
    wall_height: float = 250.0,
    wall_thickness: float = 7.5,
    overwrite: bool = False,
) -> dict
```

**Semantic decision on `width`/`height`.** A Sweet Home 3D plan is an *unbounded plane*;
the format has no home extent attribute (SCHEMA.md §5.1). So `width`/`height` cannot be
stored as such. We interpret them as a **convenience footprint**:

- If **both** are given (`> 0`), create four walls forming a closed rectangle with its
  **outer** corner at the origin — centrelines at
  `(t/2, t/2) → (W-t/2, t/2) → (W-t/2, H-t/2) → (t/2, H-t/2) → close`, where
  `t = wall_thickness`. So `width`/`height` are **exterior** dimensions. The four walls are
  mutually joined via `wallAtStart`/`wallAtEnd` in a closed cycle.
  Additionally create one room whose points are the **inner** face corners
  `(t,t), (W-t,t), (W-t,H-t), (t,H-t)`, named `name`.
- If **neither** is given, create an empty plan (no walls, no rooms).
- If exactly one is given → `INVALID_ARGUMENT` ("width and height must be given together").

`name` is written to `home/@name` in both cases and must be non-empty after `strip()`.
`wall_height` and `wall_thickness` must be `> 0` → `DEGENERATE_DIMENSION`.
`home/@wallHeight` is set to `wall_height`; `home/@version` to `5300` (SCHEMA.md §9-C).

Errors: `PROJECT_EXISTS` (unless `overwrite`), `BAD_PATH`, `DEGENERATE_DIMENSION`,
`INVALID_ARGUMENT`, `IO_ERROR`.

Returns:
```json
{ "ok": true, "project_path": "...", "name": "House",
  "walls_created": 4, "rooms_created": 1,
  "wall_ids": ["wall0","wall1","wall2","wall3"], "room_ids": ["room0"],
  "note": "width/height were interpreted as exterior dimensions of a 4-wall rectangle." }
```

## 4. `add_wall`

```python
def add_wall(
    project_path: str,
    x1: float, y1: float, x2: float, y2: float,
    thickness: float = 7.5,
    height: float | None = None,
    height_at_end: float | None = None,
    join: bool = True,
    allow_crossing: bool = False,
) -> dict
```

- `height=None` ⇒ omit `@height`, wall inherits `home/@wallHeight`.
- `height_at_end` (sloped wall) requires `height` to also be set → else `INVALID_ARGUMENT`.
- `join=True` runs the endpoint-joining algorithm (VALIDATION.md §3) and may modify
  neighbouring walls' `wallAtStart`/`wallAtEnd`.
- `allow_crossing=True` downgrades `WALL_CROSSES_WALL` from error to a returned warning.

Validation, in order: universal (§2.1) → `thickness > 0` and `height > 0` and
`height_at_end > 0` (`DEGENERATE_DIMENSION`) → length ≥ `MIN_WALL_LENGTH`
(`WALL_TOO_SHORT`) → duplicate check (`WALL_DUPLICATE`) → crossing check
(`WALL_CROSSES_WALL`).

Returns:
```json
{ "ok": true, "wall_id": "wall4", "length": 500.0,
  "joined": { "start": "wall3", "end": null },
  "warnings": [] }
```

## 5. `add_room`

```python
def add_room(
    project_path: str,
    points: list[tuple[float, float]],
    name: str | None = None,
    area_visible: bool = True,
    allow_overlap: bool = False,
) -> dict
```

- `points` is the polygon in order; **closure is implicit**. If the caller repeats the first
  point at the end, we silently drop the duplicate (this is the single most likely LLM
  mistake) and report it in `warnings`.
- Consecutive duplicate points (within `EPS_POINT`) are collapsed before validation.
- Validation: ≥3 distinct points (`ROOM_TOO_FEW_POINTS`) → `|area| ≥ MIN_ROOM_AREA`
  (`ROOM_DEGENERATE`) → simple polygon (`ROOM_SELF_INTERSECTS`) → overlap with existing
  rooms (`ROOM_OVERLAPS`, suppressible via `allow_overlap`).
- Winding is normalised (VALIDATION.md §4.5) before writing.
- `name` is not required to be unique, but a duplicate name produces a `warnings` entry
  because `room_name` lookups elsewhere will then be ambiguous.

Returns:
```json
{ "ok": true, "room_id": "room1", "name": "Kitchen",
  "point_count": 4, "area_cm2": 200000.0, "area_m2": 20.0,
  "warnings": ["Dropped a repeated closing point; room closure is implicit."] }
```

## 6. `add_furniture`

```python
def add_furniture(
    project_path: str,
    catalog_id: str,
    x: float, y: float,
    rotation: float = 0.0,               # DEGREES, clockwise in plan view
    room_name: str | None = None,
    name: str | None = None,
    width: float | None = None,
    depth: float | None = None,
    height: float | None = None,
    elevation: float = 0.0,
    allow_overlap: bool = True,
) -> dict
```

Dimension resolution follows ARCHITECTURE.md §7 strictly: explicit `width`/`depth`/`height`
override → else reference catalogue from the last `open_reference` → else built-in table →
else `UNKNOWN_CATALOG_ID`. Partial explicit dimensions are allowed only if the remainder
resolve from a catalogue; otherwise `INVALID_ARGUMENT`.

`rotation` is converted: `angle_radians = math.radians(rotation % 360)`.

`room_name` semantics — **it does not create containment** (the format has no such link;
SCHEMA.md §5.4). It is a *placement assertion*: if given, we look up the room by name
(`ELEMENT_NOT_FOUND` / `AMBIGUOUS_NAME`) and verify `(x, y)` is inside its polygon. If it is
not, we return `INVALID_ARGUMENT` with the room's bounding box in `details` — this catches
the very common LLM error of placing furniture in the wrong room. If `room_name` is `None`,
no containment check is done and the containing room (if any) is reported for information.

`name` defaults to the catalogue name, else to `catalog_id`.
All of `width`, `depth`, `height` must end up `> 0` → `DEGENERATE_DIMENSION`.
`elevation` must be `≥ 0`.

Model handling: if the resolved catalogue entry carries model bytes, they are written into
the target ZIP under a fresh entry name and `@model` is set to that name. Otherwise `@model`
is omitted entirely — **never** a dangling reference (SCHEMA.md §5.6).

Returns:
```json
{ "ok": true, "furniture_id": "furniture0", "catalog_id": "eTeks#chair",
  "name": "Chair", "x": 120.0, "y": 240.0, "rotation_degrees": 90.0,
  "width": 45.0, "depth": 45.0, "height": 90.0,
  "dimension_source": "builtin_table", "model_included": false,
  "room_name": "Kitchen",
  "warnings": ["No 3D model available for 'eTeks#chair'; the piece will appear in the plan but may not render in 3D."] }
```

## 7. `add_dimension` *(proposed addition — required by the stated goal "dimensions")*

```python
def add_dimension(
    project_path: str,
    x1: float, y1: float, x2: float, y2: float,
    offset: float = 20.0,
    label_angle: float = 0.0,          # degrees
    visible_in_3d: bool = False,
) -> dict
```
`offset` is `#REQUIRED` in the DTD; sign selects which side of the segment the line is drawn
on. Length must be ≥ `MIN_DIMENSION_LENGTH` → `DEGENERATE_DIMENSION`.
Returns `{"ok": true, "dimension_id": "dimensionLine0", "length": 500.0}`.

## 8. `list_elements`

```python
def list_elements(
    project_path: str,
    kinds: list[str] | None = None,     # subset of ["walls","rooms","furniture","dimensions"]
) -> dict
```
Read-only. Returns the `*View` projections plus a summary. Also surfaces the document-level
facts an editing model needs:

```json
{ "ok": true, "name": "House", "version": "5300",
  "wall_height_default": 250.0, "level_count": 0,
  "bounds": { "min_x": 0.0, "min_y": 0.0, "max_x": 800.0, "max_y": 600.0 },
  "counts": { "walls": 4, "rooms": 1, "furniture": 3, "dimensions": 0 },
  "walls": [ { "id": "wall0", "x_start": 3.75, ... } ],
  "rooms": [ ... ], "furniture": [ ... ], "dimensions": [ ... ],
  "unsupported_elements_present": ["environment", "observerCamera"] }
```
`unsupported_elements_present` tells the model what exists but is not editable — and is
preserved on write. Errors: `PROJECT_NOT_FOUND`, `NOT_A_ZIP`, `MISSING_HOME_XML`,
`MALFORMED_XML`.

## 9. `export_project`

```python
def export_project(project_path: str, destination_path: str | None = None) -> dict
```

**Semantic decision.** `.sh3d` *is* the storage format and the server is stateless
(ARCHITECTURE.md §4), so there is no pending state to flush. Exporting to OBJ/PNG/SVG
requires the Java application and is excluded by the no-app constraint. `export_project`
therefore means **"finalise, verify and report"**:

1. Open the project, run the full `validate_project` rule set.
2. Re-serialise `Home.xml` in canonical DTD order and rewrite the archive.
3. If `destination_path` is given, write there instead (must end `.sh3d`).
4. Return the path, a full element summary, the validation report, and the list of ZIP
   entries actually written.

Any request for a different output format returns `UNSUPPORTED_FEATURE` with a message
naming Sweet Home 3D's own export as the route.

```json
{ "ok": true, "project_path": "...", "bytes_written": 1843,
  "entries": ["Home.xml"], "validation": { "errors": [], "warnings": [] },
  "counts": { "walls": 4, "rooms": 1, "furniture": 3 },
  "note": "Legacy 'Home' and 'ContentDigests' entries are not written; Sweet Home 3D 6+ reads Home.xml in priority." }
```

## 10. `open_reference`

```python
def open_reference(sample_sh3d_path: str) -> dict
```

Read-only inspection of a Sweet Home 3D-authored file, and the population of the reference
furniture catalogue (ARCHITECTURE.md §7 tier 1). It **never** writes to
`sample_sh3d_path`.

Returns:
- the ZIP entry listing with sizes, and whether legacy `Home` / `Home.xml` / `ContentDigests`
  are present;
- the `home` element's attributes verbatim;
- a tag-frequency census of every element in the document (this is our ongoing empirical
  cross-check against docs/SCHEMA.md);
- **`unknown_tags`** and **`unknown_attributes`** — anything present in the file but absent
  from our DTD-derived table. Non-empty means SCHEMA.md needs updating; the Phase 4
  cross-check test asserts on this.
- `catalog_entries`: the resolvable `catalogId → dimensions/model` index now available to
  `add_furniture`.

The extracted catalogue is cached **in the server process only**, keyed by the reference
file's absolute path and mtime. Because the server is otherwise stateless, callers should
be told (in the tool docstring) to call `open_reference` before `add_furniture` if they want
real models. `add_furniture` degrades gracefully to tier 2/3 if it was never called.

Errors: `PROJECT_NOT_FOUND`, `NOT_A_ZIP`, `MISSING_HOME_XML` (a legacy `Home`-only file
cannot be inspected — say so explicitly, this is a real and likely case), `MALFORMED_XML`.

## 11. `validate_project` *(proposed addition)*

```python
def validate_project(project_path: str) -> dict
```
Runs every rule in VALIDATION.md over an existing document without modifying it, returning
`{"ok": true, "errors": [...], "warnings": [...]}`. Each entry carries the same
`code`/`message`/`details` shape as §2 plus the offending element id(s). Exists so a model
can check its own work after a batch of edits, and so Phase 4 can regression-test whole
fixture files.

## 12. `delete_element` *(proposed addition)*

```python
def delete_element(project_path: str, element_id: str) -> dict
```
Removes the wall / room / furniture / dimension with that `id`. For walls, also clears any
`wallAtStart`/`wallAtEnd` IDREF in other walls that pointed at it — **leaving a dangling
IDREF is a file-corrupting bug**. Errors: `ELEMENT_NOT_FOUND`.
Returns `{"ok": true, "deleted": "wall2", "kind": "wall", "references_cleared": ["wall1"]}`.

## 13. Docstring requirements (they are the tool description the LLM sees)

Every registered tool's docstring must state, in this order: one-line purpose; that lengths
are in **centimetres** and rotations in **degrees**; the coordinate convention (`y`
increases downward); what the tool does *not* do; and one concrete example call. Vague
docstrings are the main cause of malformed tool calls and are treated as bugs in review.
