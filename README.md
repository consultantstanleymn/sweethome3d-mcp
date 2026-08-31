# sweethome3d-mcp

`sweethome3d-mcp` is a local stdio MCP server for creating and editing Sweet Home 3D `.sh3d` projects on disk. It operates directly on `Home.xml` inside the ZIP archive so an LLM can add, inspect, validate, export, and delete supported plan elements without a running Sweet Home 3D instance.

This is a personal/community project. It is not affiliated with, endorsed by, or maintained by eTeks or the Sweet Home 3D project.

Verified against Sweet Home 3D version: `7.9.303.0` (`eTeks.SweetHome3D_7.9.303.0_x64`, Microsoft Store package)

## License

This repository is released under the [MIT License](LICENSE). The schema-research provenance for `docs/SCHEMA.md` and the rationale for using MIT in this repository are documented in [NOTICE.md](NOTICE.md).

## Credits / Author

Author: Stanley S Nelavala  
GitHub: [consultantstanleymn](https://github.com/consultantstanleymn)

## Install

```bash
pip install -e .
```

Run the server with:

```bash
python -m sh3d_mcp
```

## MCP Client Registration

```json
{
  "mcpServers": {
    "sweethome3d": {
      "command": "python",
      "args": ["-m", "sh3d_mcp"],
      "env": {
        "PYTHONPATH": "C:\\Users\\stanl\\Desktop\\sweethome3d-mcp\\src"
      }
    }
  }
}
```

## Worked Example

Example tool sequence for an 8 m × 6 m home with one interior wall, two rooms, one table, one dimension line, and a final export:

```python
create_project(
    project_path="house.sh3d",
    name="House",
    width=800.0,
    height=600.0,
)

add_wall(
    project_path="house.sh3d",
    x1=400.0,
    y1=7.5,
    x2=400.0,
    y2=592.5,
    join=False,
)

add_room(
    project_path="house.sh3d",
    points=[(7.5, 7.5), (400.0, 7.5), (400.0, 592.5), (7.5, 592.5)],
    name="Living Room",
    allow_overlap=True,
)

add_room(
    project_path="house.sh3d",
    points=[(400.0, 7.5), (792.5, 7.5), (792.5, 592.5), (400.0, 592.5)],
    name="Dining Room",
    allow_overlap=True,
)

add_furniture(
    project_path="house.sh3d",
    catalog_id="eTeks#table",
    x=596.25,
    y=300.0,
    room_name="Dining Room",
)

add_dimension(
    project_path="house.sh3d",
    x1=7.5,
    y1=620.0,
    x2=792.5,
    y2=620.0,
    offset=20.0,
)

export_project(project_path="house.sh3d")
```

All tool lengths are in centimetres. Tool rotations are in degrees. Plan coordinates use `x` increasing to the right. The exact positive on-screen rotation handedness and independent `y`-axis direction remain unverified because the tested Sweet Home 3D install had a broken 2-D plan view; see [docs/SCHEMA.md §9-B](docs/SCHEMA.md#9-remaining-open-questions--uncertainties).

## Limitations

- Single level only.
- No doors or windows bound to walls.
- No lights.
- No textures, materials, or colour authoring.
- No rendering or export to OBJ, PNG, or SVG.
- No live sync with a running Sweet Home 3D application.
- Output format is `.sh3d` only.

## Tool Surface

The server currently registers these tools:

- `create_project`
- `add_wall`
- `add_room`
- `add_furniture`
- `add_dimension`
- `list_elements`
- `export_project`
- `open_reference`
- `validate_project`
- `delete_element`

## Known Issues / Open Questions

These are still genuinely open and will also be tracked as GitHub issues for contributors:

- Rotation handedness and `y`-axis direction: 90° rotation magnitude and width/depth axis swap are confirmed in real Sweet Home 3D, but exact clockwise-vs-counterclockwise handedness and independent `y`-down confirmation remain unverified because the tested install's 2-D plan view was blank. This is the highest-value open item because it affects the precise semantics of rotation and some geometry interpretation. See [docs/SCHEMA.md §9-B](docs/SCHEMA.md#9-remaining-open-questions--uncertainties).
- Modern `Home.CURRENT_VERSION` integer: the project currently writes the known-safe `5300` value from a 2017 source mirror because lower is safer than accidentally claiming a newer unsupported version. The actual current integer for modern Sweet Home 3D still needs confirmation from newer source or a verified file sample. See [docs/SCHEMA.md §9-C](docs/SCHEMA.md#9-remaining-open-questions--uncertainties).
- Colour attribute encoding: colour authoring is not implemented yet, and the exact accepted wire format for colour attributes still needs direct confirmation. The current docs note decimal-or-hex uncertainty and intentionally defer the feature. See [docs/SCHEMA.md §9-D](docs/SCHEMA.md#9-remaining-open-questions--uncertainties).
- `ContentDigests` necessity: the implementation intentionally omits `ContentDigests` on write because `Home.xml` loads without it in source analysis, but it is still not fully proven whether a real Sweet Home 3D open ever requires it in any edge case. See [docs/SCHEMA.md §9-F](docs/SCHEMA.md#9-remaining-open-questions--uncertainties).
- Multi-level support: multi-floor homes remain out of scope for v1 and would be a substantial feature rather than a small patch. The format details around levels and `elevationIndex` also remain under-investigated. See [docs/SCHEMA.md §9-K](docs/SCHEMA.md#9-remaining-open-questions--uncertainties).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for practical development setup and conventions. Longer-form contributor notes and project summaries will live in the repository Wiki under [`wiki/`](wiki/).

## Attribution

The `Home.xml` schema notes in `docs/SCHEMA.md` were derived from Sweet Home 3D's published DTD and GPL-licensed source code. This project does not bundle Sweet Home 3D itself.
