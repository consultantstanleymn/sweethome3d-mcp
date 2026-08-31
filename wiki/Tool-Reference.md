# Tool Reference

This page summarizes the public MCP tool surface. For exact envelopes and edge-case behavior, see `docs/TOOL_INTERFACE.md`.

## `create_project`

Create a new `.sh3d` file, optionally with a default rectangular shell.

Key parameters:

- `project_path`
- `name`
- optional `width`, `height`
- optional `wall_height`, `wall_thickness`
- optional `overwrite`

Example:

```python
create_project(project_path="house.sh3d", name="House", width=800.0, height=600.0)
```

## `add_wall`

Add one wall by centerline coordinates.

Key parameters:

- `project_path`
- `x1`, `y1`, `x2`, `y2`
- optional `thickness`
- optional `height`, `height_at_end`
- optional `join`
- optional `allow_crossing`

Example:

```python
add_wall(project_path="house.sh3d", x1=0.0, y1=0.0, x2=500.0, y2=0.0)
```

## `add_room`

Add a room polygon from ordered points.

Key parameters:

- `project_path`
- `points`
- optional `name`
- optional `area_visible`
- optional `allow_overlap`

Example:

```python
add_room(
    project_path="house.sh3d",
    points=[(0.0, 0.0), (500.0, 0.0), (500.0, 400.0), (0.0, 400.0)],
    name="Kitchen",
)
```

## `add_furniture`

Add a piece of furniture by catalogue id and placement.

Key parameters:

- `project_path`
- `catalog_id`
- `x`, `y`
- optional `rotation`
- optional `room_name`
- optional `name`
- optional `width`, `depth`, `height`
- optional `elevation`
- optional `allow_overlap`

Example:

```python
add_furniture(
    project_path="house.sh3d",
    catalog_id="eTeks#chair",
    x=120.0,
    y=240.0,
    rotation=90.0,
)
```

## `add_dimension`

Add a dimension line between two points.

Key parameters:

- `project_path`
- `x1`, `y1`, `x2`, `y2`
- optional `offset`
- optional `label_angle`
- optional `visible_in_3d`

Example:

```python
add_dimension(project_path="house.sh3d", x1=0.0, y1=0.0, x2=500.0, y2=0.0, offset=20.0)
```

## `list_elements`

List editable project elements and summary data.

Key parameters:

- `project_path`
- optional `kinds`

Example:

```python
list_elements(project_path="house.sh3d", kinds=["walls", "rooms"])
```

## `export_project`

Validate and rewrite a project into canonical archive form.

Key parameters:

- `project_path`
- optional `destination_path`

Example:

```python
export_project(project_path="house.sh3d", destination_path="house-final.sh3d")
```

## `open_reference`

Inspect a reference `.sh3d` file and populate the in-process reference furniture catalogue.

Key parameters:

- `sample_sh3d_path`

Example:

```python
open_reference(sample_sh3d_path="reference-home.sh3d")
```

## `validate_project`

Run the read-only validation pass over an existing project.

Key parameters:

- `project_path`

Example:

```python
validate_project(project_path="house.sh3d")
```

## `delete_element`

Delete a wall, room, furniture item, or dimension by `id`.

Key parameters:

- `project_path`
- `element_id`

Example:

```python
delete_element(project_path="house.sh3d", element_id="wall2")
```
