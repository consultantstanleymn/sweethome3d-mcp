# sweethome3d-mcp

`sweethome3d-mcp` is a local stdio MCP server for creating and editing Sweet Home 3D `.sh3d` projects on disk. It operates directly on `Home.xml` inside the ZIP archive so an LLM can add, inspect, validate, export, and delete supported plan elements without a running Sweet Home 3D instance.

Verified against Sweet Home 3D version: `7.9.303.0` (`eTeks.SweetHome3D_7.9.303.0_x64`, Microsoft Store package)

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

All tool lengths are in centimetres. Tool rotations are in degrees. Plan coordinates use `x` increasing to the right and `y` increasing downward. The positive on-screen rotation direction is still unverified until Phase 4.6 completes against a real Sweet Home 3D install.

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

## Attribution

The `Home.xml` schema notes in `docs/SCHEMA.md` were derived from Sweet Home 3D's published DTD and GPL-licensed source code. This project does not bundle Sweet Home 3D itself.
