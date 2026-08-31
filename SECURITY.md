# Security Policy

## Supported versions

This project does not yet have tagged releases; the `main` branch is the only
supported line. Security fixes land there.

## Reporting a vulnerability

Please **do not** open a public issue for a security vulnerability.

Instead, use GitHub's private vulnerability reporting for this repository:
[Report a vulnerability](https://github.com/consultantstanleymn/sweethome3d-mcp/security/advisories/new)
(Security tab → "Report a vulnerability").

Include:
- What the vulnerability is and its potential impact.
- Steps to reproduce, or a minimal proof of concept.
- Which tool(s)/file(s) are affected.

You should get an initial response within a few days. This is a small,
personally-maintained open source project — please be patient, but a genuine
report will be taken seriously and fixed.

## Scope notes

This server operates on local `.sh3d` files supplied by whatever MCP client
invokes it; it does not make network calls, execute arbitrary code from a
`.sh3d` file's contents, or expose a network-facing service. The most
relevant security concerns are likely to be:

- Path handling in tools that accept a `project_path` (path traversal,
  overwriting unintended files).
- ZIP/XML parsing of untrusted `.sh3d` input (e.g. `open_reference` on a
  file you didn't create) — malformed or adversarial archives.
