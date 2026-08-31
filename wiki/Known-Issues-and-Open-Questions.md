# Known Issues and Open Questions

These items remain open after the initial implementation and verification passes. They are good candidates for focused contributions because each one is concrete and testable.

For the primary source notes behind these items, see `docs/SCHEMA.md §9`.

## B. Rotation Handedness And `y`-Axis Direction

What is already known:

- furniture angles in `Home.xml` are written in radians
- the current implementation uses `math.radians(rotation % 360)`
- real verification in Sweet Home 3D 7.9.303.0 confirmed that a 90° rotation has the correct magnitude and swaps the width/depth footprint of rectangular furniture as expected

What is still unknown:

- whether positive rotation is clockwise or counterclockwise on the 2-D plan
- whether the plan `y` axis is definitively downward in the way the docs currently infer

Why it matters:

- tool docstrings currently need to keep the handedness note marked as unverified
- exact interpretation affects rotation semantics, room winding commentary, and dimension offset sign explanations

What would resolve it:

- test against a Sweet Home 3D install with a working 2-D plan view
- create an asymmetric reference shape or non-symmetric furniture placement so clockwise vs counterclockwise is visually distinguishable
- compare observed orientation with the emitted XML angle value

## C. Modern `Home.CURRENT_VERSION` Integer

What is already known:

- the project writes `version='5300'`
- that value comes from a 2017 Sweet Home 3D source mirror
- writing a lower known-safe value is less risky than emitting a guessed newer one

What is still unknown:

- the actual `Home.CURRENT_VERSION` integer used by current Sweet Home 3D releases

Why it matters:

- it would let the project document the modern value accurately
- it may matter for long-term fidelity, even though current readers accept the older value

What would resolve it:

- inspect newer Sweet Home 3D source code
- or inspect files written by modern Sweet Home 3D and correlate them with source/documentation

## D. Colour Attribute Encoding

What is already known:

- Sweet Home 3D parses colour attributes into integer values
- the project currently does not implement colour authoring

What is still unknown:

- the exact accepted external encoding: plain decimal, hexadecimal forms, alpha handling, or multiple accepted forms

Why it matters:

- colour support should not be added on guesswork because bad attribute encoding could create invalid or misleading output

What would resolve it:

- inspect the relevant parser code in Sweet Home 3D
- create small real-app fixtures with explicit colours and compare the serialized XML

## F. Is `ContentDigests` Ever Required?

What is already known:

- the current implementation omits `ContentDigests`
- source analysis suggests `Home.xml` is read without depending on it
- XML-only files have already been confirmed to open in Sweet Home 3D 7.9.303.0

What is still unknown:

- whether there is any real-app edge case where `ContentDigests` matters for open, repair, warning suppression, or specific content recovery behavior

Why it matters:

- if it is ever required in practice, archive writing would need to grow a deterministic digest step

What would resolve it:

- collect real `.sh3d` files with missing or damaged content entries
- compare open/repair behavior with and without `ContentDigests`
- inspect the relevant reader/repair code paths in Sweet Home 3D

## K. Multi-Level / Multi-Floor Support

What is already known:

- v1 is intentionally single-level only
- the `level` schema exists, but the full semantics around `elevationIndex`, level ordering, and multi-level editing behavior were not implemented

What is still unknown:

- the exact level-management behavior needed for safe authoring, editing, validation, and deletion across multiple floors

Why it matters:

- this is not a small patch; it is a substantial feature with schema, validation, and tool-contract consequences

What would resolve it:

- gather real multi-level reference files
- extend the docs first
- design level-aware validation and tool semantics before implementing XML mutations
