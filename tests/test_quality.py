import inspect
from pathlib import Path
import re

from sh3d_mcp import server


def test_src_contains_no_print_calls() -> None:
    src_root = Path(__file__).resolve().parents[1] / "src"
    pattern = re.compile(r"\bprint\(")

    offenders: list[str] = []
    for path in src_root.rglob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(src_root.parent)))

    assert offenders == []


def test_registered_tool_docstrings_are_non_empty_and_mention_units() -> None:
    rotation_params = {"rotation", "label_angle"}
    wrapper_names = [
        "create_project",
        "add_wall",
        "add_room",
        "add_furniture",
        "add_dimension",
        "list_elements",
        "export_project",
        "open_reference",
        "validate_project",
        "delete_element",
    ]

    for wrapper_name in wrapper_names:
        wrapper = getattr(server, wrapper_name)
        docstring = inspect.getdoc(wrapper)
        assert docstring is not None
        assert docstring.strip() != ""
        assert "centimet" in docstring.lower()
        if rotation_params.intersection(inspect.signature(wrapper).parameters):
            assert "degree" in docstring.lower()
