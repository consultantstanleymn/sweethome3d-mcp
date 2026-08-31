from pathlib import Path
import re

from sh3d_mcp.errors import ErrorCode
from sh3d_mcp.geometry import primitives


def test_tool_interface_error_code_table_exactly_matches_errorcode_enum() -> None:
    tool_interface = (Path(__file__).resolve().parents[1] / "docs" / "TOOL_INTERFACE.md").read_text(encoding="utf-8")
    table_codes = re.findall(r"^\| `([A-Z_]+)` \|", tool_interface, flags=re.MULTILINE)

    assert table_codes == [error_code.value for error_code in ErrorCode]


def test_validation_tolerances_match_geometry_primitives_exactly() -> None:
    validation_doc = (Path(__file__).resolve().parents[1] / "docs" / "VALIDATION.md").read_text(encoding="utf-8")
    match = re.search(r"```python\n(.*?)```", validation_doc, flags=re.DOTALL)
    if match is None:
        raise AssertionError("Failed to locate tolerance code block in docs/VALIDATION.md")

    documented_values: dict[str, float] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, remainder = re.split(r"\s*=\s*", stripped, maxsplit=1)
        value_text = remainder.split()[0]
        documented_values[name] = float(value_text)

    for name, expected_value in documented_values.items():
        assert hasattr(primitives, name)
        assert getattr(primitives, name) == expected_value
