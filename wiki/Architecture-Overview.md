# Architecture Overview

This project is deliberately small and conservative. It is a local stdio MCP server that edits `.sh3d` files on disk. It does not talk to a running Sweet Home 3D instance, and it does not try to reimplement the Java application.

## Core Design Decision

The XML tree is the source of truth.

That choice drives most of the codebase:

- `Home.xml` is parsed into `xml.etree.ElementTree`
- tool implementations mutate the tree in place
- unknown elements and unknown attributes are preserved
- non-XML ZIP entries are copied through byte-for-byte

This avoids the main failure mode of a dataclass-only model: losing parts of the file format the project does not edit directly.

## Why The Project Rewrites ZIP Files

Every mutating tool follows the same high-level flow:

1. open the `.sh3d` archive
2. validate arguments and geometry
3. mutate the XML tree
4. write a fresh archive atomically

The server is stateless by design. There is no hidden in-memory project registry. Each tool call is self-contained and works only from `project_path`.

## What Gets Preserved And What Does Not

Preserved:

- unknown XML tags
- unknown XML attributes
- referenced content entries such as models and textures already present in the archive

Deliberately dropped on write:

- legacy `Home` entry
- `ContentDigests`

That is intentional. The project writes `Home.xml` as the authoritative representation and avoids emitting stale legacy data.

## XML And ZIP Responsibilities

The codebase keeps responsibilities narrow:

- `src/sh3d_mcp/tools/`: tool orchestration and tool-level validation flow
- `src/sh3d_mcp/sh3d/elements.py`: XML element construction and read-only projections
- `src/sh3d_mcp/sh3d/archive.py`: ZIP read/write behavior
- `src/sh3d_mcp/geometry/`: geometric predicates, joins, and validation helpers
- `src/sh3d_mcp/server.py`: MCP wrapper registration and error-envelope conversion

This separation matters because most future bugs in this project are about file integrity, not just business logic.

## Validation Philosophy

The validation rules are intentionally explicit and ordered. Mutating tools validate before saving. A failed call must not partially write.

Examples:

- duplicate and crossing walls are caught before insertion
- self-intersecting and overlapping rooms are rejected
- deleting a wall clears inbound wall-join references so the file does not retain dangling IDREFs

The tests treat write atomicity as part of the contract, not as an implementation detail.

## Scope Boundaries

The current implementation is intentionally limited:

- single-level homes only
- no wall-bound door/window semantics
- no lights
- no rendering/export via the Java app
- no live sync with Sweet Home 3D

That keeps v1 aligned with what can be done safely through ZIP/XML manipulation alone.
