# Sweet Home 3D `.sh3d` / `Home.xml` Schema

Status: derived from primary sources (not recall). All statements are tagged:
**[DTD]** = verbatim from the official DTD · **[SRC]** = read from Sweet Home 3D Java source ·
**[INF]** = inferred, see "Open questions / uncertainties".

## 1. Sources

| Source | URL | Retrieved |
|---|---|---|
| Official DTD (© 2024, SH3D 7.x) | `https://www.sweethome3d.com/SweetHome3D.dtd` | 2026-08-31, in full |
| `io/HomeXMLHandler.java` (SAX reader) | `raw.githubusercontent.com/ralic/sweethome-3d/master/SweetHome3D/src/com/eteks/sweethome3d/io/HomeXMLHandler.java` | 2026-08-31 |
| `io/HomeXMLExporter.java` (writer) | same repo/path | 2026-08-31 |
| `io/DefaultHomeOutputStream.java`, `io/DefaultHomeInputStream.java` | same repo | 2026-08-31 |
| `io/HomeFileRecorder.java`, `io/XMLWriter.java` | same repo | 2026-08-31 |
| `model/Home.java`, `model/LengthUnit.java`, `io/DefaultUserPreferences.{java,properties}` | same repo | 2026-08-31 |

`ralic/sweethome-3d` is a GitHub mirror of the GPL SourceForge tree, last pushed 2017
(≈ SH3D 6.x). The DTD is from 2024. Where the two disagree the DTD wins; divergences are
flagged in §9.

## 2. Container format (the `.sh3d` file)

A `.sh3d` file is a plain ZIP archive. **[SRC: DefaultHomeOutputStream]** Entries, in the
order Sweet Home 3D writes them:

1. `Home` — Java-serialized `com.eteks.sweethome3d.model.Home` object graph. Legacy.
2. `Home.xml` — the XML document described in this file.
3. `ContentDigests` — a text manifest used only to repair damaged files. Format
   **[SRC]**: first line `ContentDigests-Version: 1.0`, blank line, then repeating
   `Name: <entry>` / `SHA-1-Digest: <base64>` pairs. **Optional.**
4. Zero or more *content entries*: model files (`.obj`, `.zip`), textures, images,
   background images. Named by number/path and referenced by name from `Home.xml`.

### 2.1 Which entry does Sweet Home 3D read? — decisive for this project

`DefaultHomeInputStream.readHome()` **[SRC]** scans the archive for both `Home` and
`Home.xml`. If an `xmlHandler` was supplied **and** `Home.xml` exists, it seeks to and
parses `Home.xml`, **ignoring `Home` entirely**. If neither entry exists it throws
`Missing entry "Home" or "Home.xml"`.

The desktop application constructs its recorders as
`new HomeFileRecorder(0, false, prefs, false, true)` and
`new HomeFileRecorder(9, false, prefs, false, true)` **[SRC: SweetHome3D.java:181,191]**
— the trailing `true` is `preferXmlEntry`, documented as *"an additional `Home.xml` entry
will be saved in files and **read in priority** from saved files."*

**Conclusion: a ZIP containing only `Home.xml` (plus any content entries it references)
is a valid, openable `.sh3d` for Sweet Home 3D ≥ 5.3.** We never need to emit the
Java-serialized `Home` entry, and we must never attempt to.

**Verified against a real install:** a generated XML-only `.sh3d` from this project
opened successfully in **Sweet Home 3D 7.9.303.0**
(`eTeks.SweetHome3D_7.9.303.0_x64`, Microsoft Store package). Walls, rooms, and furniture
were present and correct in the 3-D view and furniture list, with no corruption warnings.

### 2.2 ZIP mechanics
- Compression: SH3D uses deflate level 0 (uncompressed) or 9. Python's `zipfile` with
  `ZIP_DEFLATED` or `ZIP_STORED` is compatible; nothing depends on the level.
- Entry names are `/`-separated, no leading slash.
- No ZIP comment, no encryption, no ZIP64 requirement for typical homes.

## 3. XML document conventions **[SRC: XMLWriter.java]**

- Prolog written by SH3D is exactly `<?xml version='1.0'?>` + `\n`. **No encoding
  declaration** (⇒ UTF-8 per XML spec) and **no `<!DOCTYPE>`**.
- Attribute values are delimited with **single quotes**.
- Indentation is two spaces per depth level.
- Entity escaping is applied to attribute values and text **[SRC: `replaceByEntities`]**.
- The parser is a **non-validating** SAX parser: it does not fetch the DTD and does not
  enforce the content models. Element order therefore is not enforced at read time — but
  we emit in DTD order anyway (see §8).

## 4. Units, axes, angles

- **Length unit is always the centimetre, everywhere in `Home.xml`.**
  **[SRC: `LengthUnit.CENTIMETER.centimeterToUnit(x) { return x; }`]** — the user's display
  unit (`unit=centimeter` default **[SRC: DefaultUserPreferences.properties:24]**) is a UI
  preference only and is *not* persisted into `Home.xml` geometry.
- Defaults from the shipped preferences **[SRC: DefaultUserPreferences.properties]**:
  `newWallThickness=7.5`, `newHomeWallHeight=250`, `newFloorThickness=12`.
- Coordinate system: 2-D plan is believed to be `x` to the right, `y` **downward** (screen
  convention); `z`/`elevation` is height above the level's floor, upward.
  **[INF — see §9-B]**
- **All angles in `Home.xml` are in radians and are written raw.** The exporter does
  `writer.writeFloatAttribute("angle", piece.getAngle())` and the handler does
  `piece.setAngle(parseOptionalFloat(attributes,"angle"))` — **no degree conversion at any
  point** **[SRC: HomeXMLExporter.java:372, HomeXMLHandler.java:1187-1189]**. This applies to
  `angle`, `nameAngle`, `areaAngle`, `pitch`, `roll`, `northDirection`, `yaw`.
- **Empirical partial verification in Sweet Home 3D 7.9.303.0:** writing furniture angles as
  `math.radians(rotation % 360)` produces the expected **magnitude and axis-swap effect** for
  rectangular furniture. A 140 cm × 70 cm desk at `rotation=0` appeared wide and shallow,
  while the same desk at `rotation=90` appeared narrow and deep in the 3-D view. This
  confirms the rotation is not ignored and that 90° swaps the width/depth footprint as
  expected. The exact clockwise-vs-counterclockwise handedness and the independent `y`-down
  direction remain unverified because the tested install's 2-D plan view was blank. See §9-B.
- Numbers are Java `float` formatted with `Float.toString`-style output; `#.#`-free plain
  decimals are accepted on read. Locale is not a factor — always `.` as decimal separator.

## 5. Element reference (verbatim DTD)

### 5.1 `home` — document root **[DTD]**
```
<!ELEMENT home (property*, furnitureVisibleProperty*, environment?, backgroundImage?,
      print?, compass?, (camera | observerCamera)*, level*,
      (pieceOfFurniture | doorOrWindow | furnitureGroup | light)*,
      wall*, room*, polyline*, dimensionLine*, label*)>
<!ATTLIST home
      version CDATA #IMPLIED
      name CDATA #IMPLIED
      camera (observerCamera | topCamera) "topCamera"
      selectedLevel CDATA #IMPLIED
      wallHeight CDATA #IMPLIED
      basePlanLocked (false | true) "false"
      furnitureSortedProperty CDATA #IMPLIED
      furnitureDescendingSorted (false | true) "false">
```
- `version` is an **integer** parsed with `Integer.parseInt`; a bad value raises
  `Invalid value for integer attribute version` **[SRC: HomeXMLHandler.java:752-757]**.
  In the 2017 mirror `Home.CURRENT_VERSION = 5300` **[SRC: Home.java:49]**. See §9-C.
- `wallHeight` is the *default* height for new walls in the UI; it is not a constraint.
- **There is no home width/height attribute. A Sweet Home 3D plan is an unbounded plane.**

### 5.2 `level` **[DTD]**
```
<!ELEMENT level (property*, backgroundImage?)>
<!ATTLIST level
      id ID #REQUIRED   name CDATA #REQUIRED
      elevation CDATA #REQUIRED   floorThickness CDATA #REQUIRED
      height CDATA #REQUIRED      elevationIndex CDATA "-1"
      visible (false | true) "true"   viewable (false | true) "true">
```
The exporter generates ids as `"level" + index`, index starting at 0
**[SRC: HomeXMLExporter.java:~97]**. If a home has **no** `<level>` elements at all, every
wall/room/piece implicitly belongs to a single unnamed ground level and their `level`
attributes are omitted — this is the normal shape of a simple single-storey home.

### 5.3 `wall` **[DTD]**
```
<!ELEMENT wall (property*, texture?, texture?, baseboard?, baseboard?)>
<!ATTLIST wall
      id ID #REQUIRED
      level IDREF #IMPLIED
      wallAtStart IDREF #IMPLIED
      wallAtEnd IDREF #IMPLIED
      xStart CDATA #REQUIRED   yStart CDATA #REQUIRED
      xEnd CDATA #REQUIRED     yEnd CDATA #REQUIRED
      height CDATA #IMPLIED    heightAtEnd CDATA #IMPLIED
      thickness CDATA #REQUIRED
      arcExtent CDATA #IMPLIED
      pattern CDATA #IMPLIED
      topColor CDATA #IMPLIED
      leftSideColor CDATA #IMPLIED     leftSideShininess CDATA "0"
      rightSideColor CDATA #IMPLIED    rightSideShininess CDATA "0">
```
- `id` is **required** on walls (unlike rooms). Exporter generates `"wall" + index`.
- Geometry is a **centreline** segment `(xStart,yStart)→(xEnd,yEnd)`; `thickness` is
  distributed symmetrically about it.
- `height` omitted ⇒ the wall uses the home's `wallHeight`. `heightAtEnd` present ⇒ sloped
  wall.
- `arcExtent` (radians) turns the wall into a circular arc bulging between the endpoints.
- **`wallAtStart` / `wallAtEnd` are single IDREFs.** Each wall endpoint can reference **at
  most one** neighbouring wall. This is the join model and its hard limitation (§ VALIDATION).
- The two optional `texture` children are distinguished by their `attribute` value
  (`leftSideTexture` / `rightSideTexture`); likewise the two `baseboard` children use
  `leftSideBaseboard` / `rightSideBaseboard`.

### 5.4 `room` and `point` **[DTD]**
```
<!ELEMENT room (property*, textStyle?, textStyle?, texture?, texture?, point+)>
<!ATTLIST room
      id ID #IMPLIED          level IDREF #IMPLIED
      name CDATA #IMPLIED
      nameAngle CDATA "0"     nameXOffset CDATA "0"   nameYOffset CDATA "-40"
      areaVisible (false | true) "false"
      areaAngle CDATA "0"     areaXOffset CDATA "0"   areaYOffset CDATA "0"
      floorVisible (false | true) "true"
      floorColor CDATA #IMPLIED    floorShininess CDATA "0"
      ceilingVisible (false | true) "true"
      ceilingColor CDATA #IMPLIED  ceilingShininess CDATA "0"
      ceilingFlat (false | true) "false">
<!ELEMENT point EMPTY>
<!ATTLIST point x CDATA #REQUIRED   y CDATA #REQUIRED>
```
- A room is a polygon given by an ordered `point+` list. **Closure is implicit** — the last
  point is joined to the first. Do **not** repeat the first point at the end.
- `<point>` children must come **after** all other children per the content model.
- The two `textStyle` children are distinguished by `attribute` = `nameStyle` / `areaStyle`;
  the two `texture` children by `floorTexture` / `ceilingTexture`.
- A room is decoupled from walls: it does not reference wall ids at all.

### 5.5 Furniture **[DTD]**
```
<!ENTITY % furnitureCommonAttributes
     'id ID #IMPLIED        name CDATA #REQUIRED
      angle CDATA "0"       visible (false | true) "true"
      movable (false | true) "true"
      description CDATA #IMPLIED   information CDATA #IMPLIED
      license CDATA #IMPLIED       creator CDATA #IMPLIED
      modelMirrored (false | true) "false"
      nameVisible (false | true) "false"
      nameAngle CDATA "0"   nameXOffset CDATA "0"   nameYOffset CDATA "0"
      price CDATA #IMPLIED'>

<!ENTITY % pieceOfFurnitureCommonAttributes
     'level IDREF #IMPLIED        catalogId CDATA #IMPLIED
      x CDATA #REQUIRED           y CDATA #REQUIRED
      elevation CDATA "0"
      width CDATA #REQUIRED       depth CDATA #REQUIRED   height CDATA #REQUIRED
      dropOnTopElevation CDATA "1"
      model CDATA #IMPLIED        icon CDATA #IMPLIED     planIcon CDATA #IMPLIED
      modelRotation CDATA "1 0 0 0 1 0 0 0 1"
      modelCenteredAtOrigin CDATA #IMPLIED
      backFaceShown (false | true) "false"
      modelFlags CDATA #IMPLIED   modelSize CDATA #IMPLIED
      doorOrWindow (false | true) "false"
      resizable (false | true) "true"
      deformable (false | true) "true"
      texturable (false | true) "true"
      staircaseCutOutShape CDATA #IMPLIED
      color CDATA #IMPLIED        shininess CDATA #IMPLIED
      valueAddedTaxPercentage CDATA #IMPLIED   currency CDATA #IMPLIED'>

<!ENTITY % pieceOfFurnitureHorizontalRotationAttributes
     'horizontallyRotatable (false | true) "true"
      pitch CDATA "0"   roll CDATA "0"
      widthInPlan CDATA #IMPLIED   depthInPlan CDATA #IMPLIED
      heightInPlan CDATA #IMPLIED'>

<!ELEMENT pieceOfFurniture (property*, textStyle?, texture?, material*, transformation*)>
<!ATTLIST pieceOfFurniture %furnitureCommonAttributes; %pieceOfFurnitureCommonAttributes;
      %pieceOfFurnitureHorizontalRotationAttributes;>

<!ELEMENT doorOrWindow (sash*, property*, textStyle?, texture?, material*, transformation*)>
<!ATTLIST doorOrWindow %furnitureCommonAttributes; %pieceOfFurnitureCommonAttributes;
      wallThickness CDATA "1"   wallDistance CDATA "0"
      wallWidth CDATA "1"       wallLeft CDATA "0"
      wallHeight CDATA "1"      wallTop CDATA "0"
      wallCutOutOnBothSides (false | true) "false"
      widthDepthDeformable (false | true) "true"
      cutOutShape CDATA #IMPLIED   boundToWall (false | true) "true">

<!ELEMENT light (lightSource*, lightSourceMaterial*, property*, textStyle?, texture?,
      material*, transformation*)>
<!ATTLIST light ... power CDATA "0.5">

<!ELEMENT furnitureGroup ((pieceOfFurniture | doorOrWindow | furnitureGroup | light)*,
      property*, textStyle?)>
<!ATTLIST furnitureGroup %furnitureCommonAttributes;
      level IDREF #IMPLIED  x/y/elevation/width/depth/height/dropOnTopElevation CDATA #IMPLIED>
```

**Critical for `add_furniture`:** the reader builds each piece by calling
`new HomePieceOfFurniture(new CatalogPieceOfFurniture(catalogId, name, ..., parseContent(icon),
parseContent(planIcon), parseContent(model), width, depth, height, ...))`
**[SRC: HomeXMLHandler.java:1111-1137]**. Therefore:

- **`catalogId` is an opaque label only.** The reader does **not** look it up in the user's
  furniture catalogue. Nothing is resolved from it.
- `name`, `width`, `depth`, `height`, `x`, `y` are `#REQUIRED` and must be supplied by us.
- `model` is a *content reference*, not an id.
- **Verified against a real install:** in **Sweet Home 3D 7.9.303.0**, a
  `pieceOfFurniture` with **no `model` attribute** renders in the 3-D view as a plain
  placeholder box sized correctly from `width` / `depth` / `height`. It is not invisible
  and does not error.

### 5.6 Content references (`model`, `icon`, `image`, texture `image`) **[SRC]**
`HomeXMLHandler.parseContent(String s)`:
```java
try   { return new ResourceURLContent(new URL(s), s.startsWith("jar:")); }
catch (MalformedURLException) { return contentContext.lookupContent(s); }  // ZIP entry name
```
So a content attribute is **either** a well-formed absolute URL (`http:`, `file:`, `jar:…!/…`)
**or** a bare name that must exist as an entry in the same `.sh3d` ZIP. Anything else raises
`Invalid content …` and the whole file fails to open. This is the single most dangerous
attribute class in the format: **never emit a content reference whose ZIP entry we did not
also write.**

### 5.7 `dimensionLine` **[DTD]**
```
<!ELEMENT dimensionLine (property*, textStyle?)>
<!ATTLIST dimensionLine
      id ID #IMPLIED        level IDREF #IMPLIED
      xStart CDATA #REQUIRED   yStart CDATA #REQUIRED   elevationStart CDATA "0"
      xEnd CDATA #REQUIRED     yEnd CDATA #REQUIRED     elevationEnd CDATA "0"
      offset CDATA #REQUIRED
      endMarkSize CDATA "10";
      angle CDATA "0"
      color CDATA #IMPLIED
      visibleIn3D (false | true) "false">
```
(The stray `;` after `"10"` is a typo **in the published DTD itself** — reproduced verbatim
above. It is harmless because the parser is non-validating.)
`offset` is the perpendicular distance from the measured segment to the drawn dimension
line; sign selects the side. It is `#REQUIRED` — emit `0` if the caller gives nothing.

### 5.8 Other elements (present in the DTD; we pass them through untouched)
`property` (`name`,`value`,`type` ∈ `STRING|CONTENT`), `furnitureVisibleProperty`,
`environment`, `backgroundImage`, `print`/`printedLevel`, `compass`, `camera`,
`observerCamera`, `textStyle`, `texture`, `material`, `transformation`, `baseboard`,
`sash`, `lightSource`, `lightSourceMaterial`, `shelfUnit`/`shelf`, `polyline`,
`label`/`text`. Full ATTLISTs are in the retrieved DTD; we do not author these in v1.

## 6. Colours
Colour attributes (`floorColor`, `leftSideColor`, `groundColor`, …) are parsed with
`parseOptionalColor` into a Java `int` RGB. Values are written as **decimal or hexadecimal
integers**, not CSS `#rrggbb`. **[INF — §9-D]** Safest emission: decimal integer of
`r*65536 + g*256 + b`.

## 7. Minimal valid document

The smallest `Home.xml` Sweet Home 3D will open (single storey, one wall, one room):

```xml
<?xml version='1.0'?>
<home version='5300' name='Demo' camera='topCamera' wallHeight='250'>
  <wall id='wall0' xStart='0.0' yStart='0.0' xEnd='500.0' yEnd='0.0' thickness='7.5' height='250.0'/>
  <room name='Living'>
    <point x='0.0' y='0.0'/>
    <point x='500.0' y='0.0'/>
    <point x='500.0' y='400.0'/>
    <point x='0.0' y='400.0'/>
  </room>
</home>
```
Packed as a ZIP with that single entry named `Home.xml`, saved with a `.sh3d` extension.

## 8. Child ordering rule we adopt
The `home` content model is a strict **sequence**, and so are `room`, `pieceOfFurniture`,
etc. The SAX reader is non-validating and will not complain about out-of-order children,
but other consumers (SweetHome3D JS viewer, FreeCAD's SH3D importer, any validating
tooling) may. **Our writer always serialises children in DTD order** by holding one list
per child type and emitting them in the declared sequence, never by appending to the tree
as calls arrive. See ARCHITECTURE.md §5.

---

## 9. Remaining open questions / uncertainties

Every item below is something I could **not** fully confirm from a primary source. Nothing
here is presented as fact elsewhere in this document.

**B. Sign convention of the `y` axis and of `angle`.**
Sweet Home 3D's plan likely uses screen coordinates with `y` increasing **downward**, and a
positive `angle` likely appears **clockwise** on screen. I did not find an explicit
statement of this in the source I read — it is inferred from the plan being a Java2D
component. Manual verification in **Sweet Home 3D 7.9.303.0** confirmed that a 90° rotation
written by this project has the correct **magnitude** and swaps a rectangular furniture
footprint between width/depth axes as expected, but the exact clockwise-vs-counterclockwise
handedness and the independent `y`-axis direction could not be confirmed because the tested
install's 2-D plan view was blank. This still affects the precise interpretation of
furniture rotation direction, room winding/shoelace sign, and dimension-line `offset` sign.
*Action:* confirm against a working 2-D plan view. Until then, rotation-related docstrings
should keep the handedness note marked as unverified.

**C. Correct `version` integer for current Sweet Home 3D.**
`Home.CURRENT_VERSION = 5300` in the 2017 mirror. Modern releases certainly use a higher
value (7.x is plausibly `7000`+), but I could not read a current `Home.java`. Writing a
*lower* version is the safe direction: a newer reader accepts it, whereas a too-high value
may trigger a "created by a newer version" warning. **Decision: always emit `version='5300'`.**
The attribute is `#IMPLIED` so omitting it is also legal.

**D. Colour attribute encoding.**
`parseOptionalColor` yields an `int`; I did not read its body, so I cannot state whether it
accepts `#rrggbb`, `0x…`, plain decimal, or all three, nor whether the high byte carries
alpha. *Action:* read `HomeXMLHandler.parseOptionalColor` before implementing any colour
feature. v1 emits no colour attributes at all, so this is deferred.

**F. Is `ContentDigests` ever required?**
It appears to be repair metadata only, and `DefaultHomeInputStream` reads `Home.xml`
without consulting it. Not verified that its absence is always benign. We omit it; flag if a
real SH3D open ever complains.

**G. `shelfUnit` is not in the `home` content model.**
The 2024 DTD declares `<!ELEMENT shelfUnit …>` but `home`'s content model lists only
`pieceOfFurniture | doorOrWindow | furnitureGroup | light`. Either the DTD is internally
inconsistent, or `shelfUnit` only appears nested. Irrelevant to v1; noted for completeness.

**H. `lightSourceMaterial`'s ATTLIST is malformed in the published DTD**
(`<!ATTLIST lightSourceMaterial name #REQUIRED>` — missing the `CDATA` type). Another
upstream DTD bug. Confirms the DTD is documentation, not a validation contract.

**I. Numeric formatting fidelity.**
SH3D writes Java `float`s. Python `float` is a double; naive `repr()` can produce more
digits than SH3D would (`0.1` → `0.1` is fine, but computed values may differ in the 8th
digit). Not a correctness problem for the reader (it does `Float.parseFloat`), but it means
our output is never byte-identical to SH3D's. *Decision:* format all lengths/angles with
`repr(round(v, 6))`-style trimming; document that byte-identity is a non-goal.

**J. Exact escaping set in `XMLWriter.replaceByEntities`.**
I saw the method is called but did not read its body. Python's `ElementTree` escapes
`& < >` in text and `& < > "` in attributes, which is a superset-safe behaviour for any
conformant XML parser. No action needed, but noted since we are not byte-matching.

**K. Multi-level (`<level>`) semantics for `elevationIndex` and level ordering.**
Not investigated. v1 is single-level only; multi-level support is explicitly out of scope
and must not be half-implemented.
