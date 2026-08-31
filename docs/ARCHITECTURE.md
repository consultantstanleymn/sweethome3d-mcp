# Architecture

## 1. Scope

A local, stdio-based MCP server that creates and edits Sweet Home 3D `.sh3d` files on disk.
No running Sweet Home 3D instance is involved, ever. No network access at runtime.

Out of scope for v1 (state as errors, do not half-build): multi-level homes, doors/windows
bound to walls, lights, textures/materials/colours, cameras and 3-D environment, rendering
or export to OBJ/PNG/SVG (these require the Java application).

## 2. Language decision: **Python 3.10+**

| Need | Python | TypeScript / Node |
|---|---|---|
| ZIP read + write | `zipfile` — **stdlib** | none in stdlib; needs `jszip`/`adm-zip`/`yauzl` |
| XML parse + serialise | `xml.etree.ElementTree` — **stdlib** | none in stdlib; needs `fast-xml-parser`/`sax`/`xmlbuilder2` |
| MCP SDK | `mcp` (official `modelcontextprotocol/python-sdk`), mature, `FastMCP` decorator API | `@modelcontextprotocol/sdk`, equally mature |
| Total runtime dependencies | **1** (`mcp`) | **3** (SDK + zip + XML) |
| Geometry (floats, tuples, `math`) | stdlib | stdlib |

Both MCP SDKs are first-party and equally capable, so the tiebreaker is exactly the stated
constraint — *minimal dependencies, standard library zip/XML where possible*. Python wins
decisively: it needs **zero** third-party libraries for the entire file-format layer.
Node cannot read a ZIP at all without a dependency.

**Decision: Python 3.10+. Runtime dependency set = `{mcp}`. Dev-only = `{pytest}`.**
No `pydantic` (the MCP SDK vendors what it needs), no `lxml`, no `numpy`.

### 2.1 Known consequence, accepted
`ElementTree` writes `<?xml version='1.0' encoding='utf-8'?>` with **double-quoted**
attributes, whereas Sweet Home 3D writes `<?xml version='1.0'?>` with **single-quoted**
attributes. These are XML-equivalent; every conformant parser (including SH3D's SAX reader)
treats them identically. **Byte-identity with SH3D output is an explicit non-goal.** Do not
hand-roll a serialiser to chase it.

## 3. The central architectural decision: the XML tree is the source of truth

Because `open_reference` and all edit operations must round-trip files that Sweet Home 3D
itself wrote, a "parse into typed dataclasses → re-serialise from dataclasses" design is
**forbidden**: it would silently destroy every `environment`, `camera`, `observerCamera`,
`texture`, `material`, `transformation`, `baseboard`, `property`, `polyline`, `label`,
`compass` and `print` element, plus every attribute we didn't model — and would orphan the
ZIP's content entries.

**Design: `xml.etree.ElementTree.Element` is the model.**

- `Sh3dDocument` holds (a) the parsed `Home.xml` `ElementTree`, and (b) the raw bytes of
  **every other ZIP entry**, keyed by entry name.
- All tools **mutate the tree in place** — insert/find/update `Element` nodes.
- Typed dataclasses (`WallView`, `RoomView`, `FurnitureView`) exist **only as read-only
  projections** for `list_elements` output. They are never a serialisation source.
- On write, all non-`Home.xml` entries are copied through **byte-for-byte**, unmodified.
  The legacy `Home` entry, if present in a file we opened, is **dropped** (it would be stale
  and the reader prefers `Home.xml` anyway — see SCHEMA.md §2.1). `ContentDigests` is also
  dropped, since it would no longer match. **This is the one deliberate lossy step and it
  must be documented in the tool's response.**

Unknown elements and unknown attributes therefore survive every edit untouched. This is
what makes `open_reference` → edit → save safe.

## 4. Statelessness

No server-side session objects, no in-memory project registry. **Every mutating tool takes
`project_path` and performs open → validate → mutate → atomic-write.** Rationale: an MCP
server can be restarted or run concurrently; file-path addressing is the only thing that
survives that, and it makes each tool independently testable. The cost is re-reading the
ZIP per call, which is microseconds for realistic homes.

`export_project` therefore does **not** flush hidden state; see TOOL_INTERFACE.md §9.

### 4.1 Atomic write
Write to `<target>.tmp-<pid>-<counter>` in the same directory, `os.replace()` onto the
target. Never truncate the user's file before the new bytes are complete.

## 5. Serialisation ordering
`Sh3dDocument.save()` reorders `<home>`'s children into DTD sequence before writing:
```
property*, furnitureVisibleProperty*, environment?, backgroundImage?, print?, compass?,
(camera|observerCamera)*, level*, (pieceOfFurniture|doorOrWindow|furnitureGroup|light)*,
wall*, room*, polyline*, dimensionLine*, label*
```
Implemented as a stable partition by tag against a fixed rank table in
`sh3d/constants.py::HOME_CHILD_ORDER`; unknown tags sort last, preserving their relative
order. Same treatment for `<room>` (all `point` children must come last).

## 6. ID allocation
- Walls require `id` (SCHEMA.md §5.3). Rooms, dimension lines and furniture take an optional
  `id`; **we always assign one** so tools can address elements later.
- Scheme matches SH3D's: `wall0, wall1, …`, `room0, …`, `level0, …`, plus
  `furniture0, …`, `dimensionLine0, …` for element types SH3D leaves unlabelled.
- `IdAllocator` scans **all** existing `id` attributes in the document on load and issues
  `f"{prefix}{n}"` for the smallest unused `n`. It must never reuse an id, even after a
  delete, within one document load.

## 7. Furniture catalogue strategy

`add_furniture(catalog_id, …)` faces the fact established in SCHEMA.md §5.5: **the reader
does not resolve `catalogId` against any catalogue.** We must supply `name`, `width`,
`depth`, `height` ourselves, and a `model` reference is only valid if the model file is
actually inside our ZIP (SCHEMA.md §5.6).

Three tiers, in order of preference at call time:

1. **Reference-file catalogue.** When `open_reference(sample_sh3d_path)` is called, we index
   every `pieceOfFurniture` in that file: `catalogId → (name, width, depth, height, model
   entry name, modelRotation, icon)`, and cache the referenced **model bytes** from that
   ZIP. `add_furniture` with a matching `catalog_id` then copies those model bytes into the
   target `.sh3d` under a fresh entry name and emits a correct `model` reference. This is
   the only path that yields real 3-D geometry, and it is why `open_reference` exists.
2. **Built-in dimension table.** A small hand-curated `catalog.py` map of the ~30 most common
   eTeks default catalogue ids (`eTeks#chair`, `eTeks#doubleBed`, `eTeks#table`, …) → name +
   nominal `width/depth/height` in cm, with **no** `model`. Produces a correctly sized
   footprint in the plan; 3-D appearance is unverified (SCHEMA.md §9-E).
3. **Explicit dimensions.** Caller passes `width`/`depth`/`height` directly with an arbitrary
   `catalog_id`; we emit a model-less piece.

If none of the three can supply dimensions, `add_furniture` **fails with
`UNKNOWN_CATALOG_ID`** listing the available ids. It never guesses a size.

Never emit a `jar:file:...` model URL pointing into a Sweet Home 3D installation: it is
machine-specific and breaks the file for anyone else.

## 8. Project layout

```
sweethome3d-mcp/
├── PLAN.md
├── README.md
├── pyproject.toml                  # [project] name, deps=["mcp"], entry point
├── docs/
│   ├── SCHEMA.md
│   ├── ARCHITECTURE.md
│   ├── TOOL_INTERFACE.md
│   └── VALIDATION.md
├── src/sh3d_mcp/
│   ├── __init__.py
│   ├── __main__.py                 # python -m sh3d_mcp  → server.main()
│   ├── server.py                   # FastMCP instance, @mcp.tool registrations, main()
│   ├── errors.py                   # Sh3dError + ErrorCode enum
│   ├── catalog.py                  # BUILTIN_CATALOG + ReferenceCatalog
│   ├── sh3d/
│   │   ├── __init__.py
│   │   ├── constants.py            # CM units, defaults, HOME_CHILD_ORDER, ROOM_CHILD_ORDER
│   │   ├── archive.py              # read_entries() / write_sh3d() — zipfile only
│   │   ├── document.py             # Sh3dDocument: open/create/save, IdAllocator
│   │   └── elements.py             # make_wall(), make_room(), … + *View dataclasses
│   ├── geometry/
│   │   ├── __init__.py
│   │   ├── primitives.py           # Pt, dist, seg_intersect, shoelace, obb corners
│   │   ├── validation.py           # every rule in VALIDATION.md
│   │   └── joins.py                # wall endpoint joining
│   └── tools/
│       ├── __init__.py
│       ├── project.py              # create_project, export_project, validate_project
│       ├── walls.py                # add_wall
│       ├── rooms.py                # add_room
│       ├── furniture.py            # add_furniture
│       ├── dimensions.py           # add_dimension
│       └── inspect.py              # list_elements, open_reference, delete_element
└── tests/
    ├── conftest.py
    ├── test_archive.py  test_document.py  test_geometry.py
    ├── test_walls.py  test_rooms.py  test_furniture.py
    ├── test_roundtrip.py           # unknown-element preservation
    └── test_schema_conformance.py  # emitted attrs ⊆ DTD attrs
```

Rule enforced by review: **`tools/*.py` contains no XML string literals and no `zipfile`
calls.** All XML construction lives in `sh3d/elements.py`; all ZIP handling in
`sh3d/archive.py`. This is what lets Phase 3 items be handed out independently.

## 9. MCP server registration and run model

Standard stdio server. `src/sh3d_mcp/server.py`:

- Create one module-level `FastMCP("sweethome3d")` instance.
- Register each tool with `@mcp.tool()` on a thin wrapper that has a full type-annotated
  signature and a docstring (FastMCP derives the JSON Schema and the tool description from
  these — the docstring is user-facing LLM-facing text, write it accordingly).
- Each wrapper does exactly: coerce/validate args → call the `tools/*.py` implementation →
  return a JSON-serialisable `dict`. Catch `Sh3dError` and return the structured error
  envelope from TOOL_INTERFACE.md §2; let nothing else escape as a bare traceback.
- `def main(): mcp.run()` — `mcp.run()` defaults to the stdio transport.
- `__main__.py` is `from .server import main; main()`.
- `pyproject.toml` declares `[project.scripts] sweethome3d-mcp = "sh3d_mcp.server:main"`.

**Absolute constraint: nothing may ever write to `stdout`.** On a stdio MCP server, stdout
is the JSON-RPC channel and a stray `print()` corrupts the protocol. All logging goes to
`stderr` via `logging.basicConfig(stream=sys.stderr)`. Add a Phase 4 test that greps the
source for bare `print(`.

Client registration (goes in README):
```json
{ "mcpServers": {
    "sweethome3d": {
      "command": "python",
      "args": ["-m", "sh3d_mcp"],
      "env": { "PYTHONPATH": "C:\\Users\\stanl\\Desktop\\sweethome3d-mcp\\src" }
} } }
```

## 10. Path safety
Every `project_path` is `Path(p).expanduser().resolve()`. Reject a path whose suffix is not
`.sh3d` (case-insensitive) with `BAD_PATH`. Reject writing to a path that exists and is not
a regular file. No sandboxing beyond this — the server is local and trusted — but the suffix
check prevents an LLM from overwriting arbitrary files through a typo.
