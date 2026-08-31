# Contributing

This repository is small enough that the fastest way to contribute is to read the code and the design docs first, then make a focused change with tests.

## Development Setup

Install in editable mode with dev dependencies:

```bash
pip install -e .[dev]
```

Run the test suite with:

```bash
pytest tests/ -q
```

If you want to run the MCP server locally:

```bash
python -m sh3d_mcp
```

## Read These First

- `docs/ARCHITECTURE.md`
- `docs/VALIDATION.md`
- `docs/TOOL_INTERFACE.md`
- `docs/SCHEMA.md`

Those documents are not optional background reading. Most of the implementation constraints come directly from them.

## Core Project Conventions

- The XML tree is the source of truth. Do not replace round-tripping with a lossy dataclass-only model.
- Mutating tools must not partially write. Validation happens before `doc.save()`, and a failed tool call must leave the `.sh3d` file unchanged.
- `stdout` is the MCP transport. Never use `print()` anywhere in server/runtime code. Log only to `stderr`.
- `tools/*.py` should stay thin. XML construction belongs in `src/sh3d_mcp/sh3d/elements.py`; ZIP handling belongs in `src/sh3d_mcp/sh3d/archive.py`.
- Unknown XML elements and attributes must survive round-trip unchanged unless there is an explicit reason to remove them.

## PLAN.md

`PLAN.md` is the implementation task list used to build the project. Most Phase 2-4 items are now historical and complete, but the file is still useful because it shows the expected granularity for new work:

- name the target module
- define the signature
- define validation order
- define test requirements

If you propose a new tool, follow that style instead of describing the change vaguely.

## Proposing a Fix or New Tool

For a bug fix:

- identify the failing behavior
- point to the relevant rule in `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, or `docs/TOOL_INTERFACE.md`
- add or update a regression test
- keep the fix narrow unless the surrounding code is already inconsistent

For a new tool:

- describe the exact tool signature
- define the success envelope and error cases
- say what existing XML elements or ZIP entries it is allowed to mutate
- define validation order explicitly
- add tests for both the happy path and no-partial-write failure path if the tool mutates

## Code Style

- Match the existing `tools/*.py` conventions.
- Public tool functions and MCP wrappers should have full type-annotated signatures.
- Tool docstrings must mention centimetres, and for rotation-taking tools must mention degrees.
- Keep comments short and only where they explain something non-obvious.
- Prefer small helper functions over inlining repeated XML or validation logic.

## Documentation

If behavior changes, update the docs in the same change:

- `docs/TOOL_INTERFACE.md` for tool contract changes
- `docs/VALIDATION.md` for geometry/validation changes
- `docs/ARCHITECTURE.md` for design or persistence changes
- `docs/SCHEMA.md` for file-format findings

Open questions intended for future contributors are also summarized in `README.md` and the Wiki.
