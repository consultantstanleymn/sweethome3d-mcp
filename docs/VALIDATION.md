# Geometry Validation

All algorithms operate in centimetres in the plan plane. Implemented in
`src/sh3d_mcp/geometry/{primitives,validation,joins}.py`. Every rule below has a section
number; TOOL_INTERFACE.md and PLAN.md reference these numbers.

## 1. Tolerances (single source of truth: `geometry/primitives.py`)

```python
EPS_POINT            = 1e-3      # 0.01 mm — two points are "the same"
EPS_PARALLEL         = 1e-9      # cross-product magnitude below this ⇒ parallel
JOIN_TOLERANCE       = 2.0       # cm — endpoints within this distance are joined
MIN_WALL_LENGTH      = 1.0       # cm
MIN_WALL_THICKNESS   = 0.1       # cm
MIN_DIMENSION_LENGTH = 0.1       # cm
MIN_ROOM_AREA        = 100.0     # cm² (10 cm × 10 cm)
ROOM_OVERLAP_TOL     = 1.0       # cm² of intersection tolerated as touching
```

`JOIN_TOLERANCE = 2.0 cm` is chosen deliberately: it is smaller than the thinnest plausible
wall (`7.5 cm` default) so it cannot fuse two walls that were meant to be distinct, but
large enough to absorb an LLM emitting `299.99` where it meant `300`. It is a module
constant, not a magic number, and every use site references it.

Floating-point rule: never compare coordinates with `==`. All predicates go through
`almost_equal(a, b, eps)` in `primitives.py`.

## 2. Degenerate and negative dimension rejection (§2)

Applied before any geometric reasoning, by `validation.check_scalars()`.

| Quantity | Rule | Error |
|---|---|---|
| any coordinate | finite, `abs ≤ 1e6` | `INVALID_ARGUMENT` |
| wall `thickness` | `> MIN_WALL_THICKNESS` | `DEGENERATE_DIMENSION` |
| wall `height`, `height_at_end` | `None` or `> 0` | `DEGENERATE_DIMENSION` |
| wall length `hypot(dx,dy)` | `≥ MIN_WALL_LENGTH` | `WALL_TOO_SHORT` |
| furniture `width`,`depth`,`height` | `> 0` | `DEGENERATE_DIMENSION` |
| furniture `elevation` | `≥ 0` | `DEGENERATE_DIMENSION` |
| room `abs(shoelace_area)` | `≥ MIN_ROOM_AREA` | `ROOM_DEGENERATE` |
| dimension line length | `≥ MIN_DIMENSION_LENGTH` | `DEGENERATE_DIMENSION` |
| `create_project` width/height | `> 2 * wall_thickness` | `DEGENERATE_DIMENSION` |

`NaN` must be caught explicitly with `math.isfinite`, because **every** comparison against
`NaN` is `False` — a naive `if v <= 0: reject` lets `NaN` straight through. This is a real
bug class here, since LLM-produced JSON can carry `NaN`-ish values.

Zero-length walls are the single most common malformed input (`add_wall(0,0,0,0,…)`) and
must produce `WALL_TOO_SHORT`, not a silently written degenerate element.

## 3. Wall joining at shared endpoints (§3)

### 3.1 The format's constraint, and its consequence
`wallAtStart` and `wallAtEnd` are **single `IDREF`s** (SCHEMA.md §5.3). A wall endpoint can
name exactly **one** neighbour. Sweet Home 3D uses these references to miter the wall ends
so the corner renders as a solid join rather than two overlapping boxes.

**Therefore a T-junction or any 3+-way junction cannot be fully expressed.** At a point
where three wall ends meet, at most one reciprocal pair can be recorded; the third wall's
end stays unjoined and Sweet Home 3D will render a butt end there. This is a limitation of
the file format, not of our implementation. We handle it as follows and **report it**:
`add_wall` returns a warning `"Endpoint at (x,y) already has 2 walls joined; this wall's end
was left unjoined (Sweet Home 3D supports only pairwise wall joins)."`

### 3.2 Algorithm — `joins.join_new_wall(doc, new_wall)`

For each of the new wall's two endpoints `P` (start, then end):

1. **Candidate search.** Iterate all existing walls `W` on the same level. For each of `W`'s
   two endpoints `Q`, compute `d = dist(P, Q)`. Collect `(W, which_end, d)` for every
   `d ≤ JOIN_TOLERANCE`.
2. **Skip occupied ends.** Discard candidates where `W`'s corresponding IDREF attribute is
   already set to some other wall — that end is taken (§3.1).
3. **Pick nearest.** Sort surviving candidates by `d`; ties broken by wall id for
   determinism (never rely on document order alone, it makes tests flaky). Take the first.
4. **Write reciprocally.** Set `new_wall/@wallAtStart` (or `@wallAtEnd`) `= W.id`, **and**
   set `W/@wallAtStart` or `W/@wallAtEnd` `= new_wall.id` on the matching end. A one-sided
   reference is a corruption: Sweet Home 3D's model expects the pair.
5. **Snap.** If `0 < d ≤ JOIN_TOLERANCE`, move the new wall's endpoint exactly onto `Q`.
   Snapping the *new* wall (never the existing one) keeps the operation non-destructive and
   makes joins idempotent. Report the snap distance in `warnings` if `d > EPS_POINT`.
6. **Self-join guard.** A wall may join its own other end (a closed 2-wall shape is
   nonsense, but a wall whose start and end coincide is already rejected by §2). Explicitly
   forbid `W is new_wall`.

Complexity is `O(n)` per insertion, trivially fast for realistic homes; do not build a
spatial index in v1.

### 3.3 Closed loops
`create_project`'s rectangle builds the cycle explicitly:
`wall0.end↔wall1.start`, `wall1.end↔wall2.start`, `wall2.end↔wall3.start`,
`wall3.end↔wall0.start`. Assert in a test that all eight IDREFs are set and mutually
consistent — this is the canonical example of a correctly joined plan.

### 3.4 Validation pass (used by `validate_project`)
- Every `wallAtStart`/`wallAtEnd` resolves to an existing wall id → else
  `ELEMENT_NOT_FOUND` (dangling IDREF; a file that will misbehave in SH3D).
- Every reference is reciprocal → else a **warning** `"Non-reciprocal wall join"`.
- Referenced endpoints are within `JOIN_TOLERANCE` of each other → else a warning
  `"Walls are joined by reference but their endpoints are N cm apart"`.

## 4. Room closure and polygon validity (§4)

### 4.1 Implicit closure — normalisation first
The DTD is `point+` with implicit closure (SCHEMA.md §5.4). Before validating:
1. If `dist(points[0], points[-1]) ≤ EPS_POINT` and `len ≥ 4`, **drop the last point** and
   emit the warning from TOOL_INTERFACE.md §5. Emitting the duplicate would create a
   zero-length final edge, which breaks self-intersection tests and can render as an
   artefact.
2. Collapse any run of consecutive points within `EPS_POINT` down to one.
3. Optionally, drop points that are collinear with their neighbours (cross product magnitude
   `< EPS_PARALLEL` after normalisation). Do this **only** as a warning-free cleanup, and
   only if it leaves ≥ 3 points.

### 4.2 Minimum point count
After normalisation, `len(points) ≥ 3` → else `ROOM_TOO_FEW_POINTS`. Two points can never
bound an area.

### 4.3 Area — shoelace
```
A2 = Σ_{i=0}^{n-1} (x_i * y_{i+1} - x_{i+1} * y_i)      # indices mod n
area = abs(A2) / 2
```
`area < MIN_ROOM_AREA` → `ROOM_DEGENERATE`. This single check catches all-collinear point
sets, "bowtie" polygons that cancel to zero, and microscopic rooms — it is the cheapest and
highest-value room check.

Report `area_cm2` and `area_m2 = area/10000` in the response; Sweet Home 3D computes and
displays the same value from these points, so the tool's number and the app's must agree —
make that a test.

### 4.4 Simplicity (no self-intersection)
`O(n²)` pairwise segment test over the `n` closed edges. For each pair of edges
`(i, i+1)` and `(j, j+1)` with `j > i`:
- **Skip adjacent pairs** (`j == i+1`, and the wrap-around pair `i == 0, j == n-1`) — they
  legitimately share exactly one endpoint.
- For all other pairs, test **proper** intersection using orientation signs:
  ```
  o1 = orient(p1,p2,p3); o2 = orient(p1,p2,p4)
  o3 = orient(p3,p4,p1); o4 = orient(p3,p4,p2)
  proper = (o1*o2 < 0) and (o3*o4 < 0)
  ```
  where `orient(a,b,c) = (b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x)`, with values whose
  magnitude is `< EPS_PARALLEL` treated as `0`.
- Additionally treat as intersecting the **collinear-overlap** case: all four orientations
  ≈ 0 **and** the projections of the two segments onto their shared direction overlap on
  more than a point.
- Non-adjacent edges sharing a single endpoint (a "pinched" polygon touching itself at a
  vertex) is also non-simple → flag it.

Any hit → `ROOM_SELF_INTERSECTS`, with `details: {"edges": [i, j]}` so the caller can fix the
specific point order. `O(n²)` is correct here: rooms have <20 points; a sweep line would be
unjustified complexity.

### 4.5 Winding normalisation
After validation, force a consistent winding by checking the sign of `A2` (§4.3) and
reversing the point list if needed. Sweet Home 3D itself tolerates either winding, so this
is for **our** determinism (stable output, comparable fixtures, consistent point-in-polygon
sign), not for the app.

**Which sign is "clockwise on screen" depends on the `y`-down convention flagged in
SCHEMA.md §9-B.** Do not encode a claim about clockwise/counter-clockwise in a comment until
that is verified. Encode only: `if A2 < 0: points.reverse()`, i.e. normalise `A2 > 0`.

### 4.6 Room–room overlap
For each existing room, compute whether the new polygon's interior overlaps it:
1. **Broad phase:** axis-aligned bounding-box rejection. Disjoint boxes ⇒ no overlap. This
   eliminates almost all pairs in a real floor plan.
2. **Narrow phase, in this order (cheapest decisive test first):**
   a. any *proper* edge-crossing between the two polygons (§4.4 predicate) ⇒ overlap;
   b. any vertex of A strictly inside B, or of B strictly inside A ⇒ overlap
      (this catches full containment, which produces no edge crossings at all — the case a
      naive implementation misses);
   c. otherwise ⇒ no overlap.
3. **Shared walls must not trip it.** Adjacent rooms in a floor plan share an edge exactly.
   Using *proper* crossing (strict sign change) and *strict* point-in-polygon means
   edge-sharing and vertex-touching produce no overlap, which is the desired behaviour.
   `ROOM_OVERLAP_TOL` exists for the case where a caller is 0.5 cm off; treat a detected
   overlap as real regardless — the tolerance is applied by nudging the strict tests with
   `EPS_POINT`, not by computing an intersection area (which would require polygon
   clipping and is out of scope).

Result → `ROOM_OVERLAPS` naming the existing room's id and name, suppressible with
`allow_overlap=True` (legitimate for mezzanines and for a room drawn over a hallway).

**Point-in-polygon** (`primitives.point_in_polygon`) is the standard ray-casting parity
test with the half-open edge rule (`(y_i > py) != (y_j > py)`) to avoid double-counting
vertices. Points *on* an edge are explicitly detected first and reported as "on boundary",
which the callers then treat as inside (for `room_name` containment) or not-inside (for
overlap detection). Making that distinction explicit avoids the classic
sometimes-inside-sometimes-not bug.

## 5. Wall overlap and crossing (§5)

### 5.1 Duplicate / collinear-overlapping walls → `WALL_DUPLICATE`
Two walls are duplicates if their centrelines are collinear (both endpoint pairs have
`orient` ≈ 0 within `EPS_PARALLEL`) **and** their 1-D projections onto the shared direction
overlap by more than `MIN_WALL_LENGTH`. This catches the common LLM failure of re-issuing
`add_wall` with the same coordinates, or drawing a second wall along an existing one.
Reversed direction (`x1,y1,x2,y2` swapped) counts as a duplicate.

### 5.2 Proper crossing → `WALL_CROSSES_WALL`
Two wall centrelines that *properly* cross (strict sign change on all four orientations,
§4.4) form an X-junction that Sweet Home 3D cannot join and that almost always indicates a
mistake. Default: error. `allow_crossing=True` downgrades it to a warning — real plans
occasionally need it, so it must be possible, just not accidental.

Endpoint-touching (T-junctions, corners) is **not** a crossing and must not be flagged; this
is exactly why the *proper* (strict) predicate is used rather than a general
segment-intersection test.

### 5.3 What we deliberately do **not** check
Thickness-aware overlap of the wall *bodies* (two near-parallel walls 3 cm apart whose 7.5 cm
bodies intersect). It requires oriented-bounding-box intersection and produces false
positives at every corner, where wall bodies legitimately overlap. Out of scope for v1;
recorded here so nobody assumes it was forgotten.

## 6. Furniture overlap (§6)

Furniture footprint = the oriented rectangle centred on `(x, y)`, of size `width × depth`,
rotated by `angle`. Corners:
```
for (sx, sy) in [(-w/2,-d/2), (w/2,-d/2), (w/2,d/2), (-w/2,d/2)]:
    corner = (x + sx*cos(a) - sy*sin(a),  y + sx*sin(a) + sy*cos(a))
```
Overlap between two such rectangles is tested with the **separating-axis theorem**: project
both rectangles onto the 4 candidate axes (the 2 edge normals of each rectangle); if the
projections are disjoint on any axis, they do not overlap.

**Default is a warning, not an error** (`allow_overlap=True` by default). Furniture
overlapping is often intentional — a rug under a table, a chair tucked under a desk, a
picture on a wall. Making this a hard error would be actively wrong. It is surfaced in
`warnings` so a model can notice an accidental stack.

`elevation` is ignored in the 2-D test; a note is added when the two pieces'
`[elevation, elevation+height]` ranges are disjoint, since that means they cannot really
collide.

## 7. Validation ordering contract

Every mutating tool runs, in this exact order, and stops at the first error:
1. Universal argument checks (TOOL_INTERFACE.md §2.1)
2. Scalar/degeneracy checks (§2)
3. Shape-intrinsic checks (room simplicity §4.4, area §4.3)
4. Document-relative checks (wall duplicate/crossing §5, room overlap §4.6, furniture
   overlap §6)
5. Mutation + joining (§3)
6. Re-serialise in DTD order and atomically write

Nothing is written to disk unless steps 1–4 pass. **There is no partial write.** A tool that
fails must leave the `.sh3d` byte-identical to how it found it — assert this in tests by
hashing the file before and after a failing call.
