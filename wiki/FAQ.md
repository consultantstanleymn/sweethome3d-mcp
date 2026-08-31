# FAQ

## Why not drive the Sweet Home 3D Java application directly?

The project is intentionally file-based. It edits `.sh3d` archives locally through Python's ZIP/XML tooling and does not require a running desktop app. That keeps the runtime dependency surface small and makes every tool call deterministic and testable.

## Why is this repository MIT instead of GPL?

The repository code is MIT-licensed. The schema research in `docs/SCHEMA.md` was derived from Sweet Home 3D's published DTD and GPL source analysis, and that provenance is documented in `NOTICE.md`. Read `NOTICE.md` for the rationale and boundaries rather than relying on a short FAQ summary.

## Does this support doors, windows, multi-level homes, lights, or rendering?

Not in v1.

Current scope excludes:

- wall-bound door/window behavior
- multi-level editing
- lights
- texture/material/colour authoring
- export/rendering through the Java application

See `README.md` and `docs/ARCHITECTURE.md` for the current scope boundaries.

## Does model-less furniture work?

Yes in current verified behavior. In Sweet Home 3D 7.9.303.0, furniture written without a `model` attribute renders as a correctly sized placeholder box in 3-D.

## How do I add a new tool?

Start with `docs/TOOL_INTERFACE.md`, `docs/ARCHITECTURE.md`, and `docs/VALIDATION.md`. Define the signature, success envelope, validation order, and no-partial-write behavior first. Then implement the XML mutation in the existing module structure and add tests for both success and failure cases.

`PLAN.md` is also useful as a template because it shows the level of specificity expected for tool work.
