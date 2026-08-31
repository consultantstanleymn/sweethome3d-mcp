import asyncio

from sh3d_mcp.server import mcp

EXPECTED_TOOL_REQUIRED_PARAMS = {
    "create_project": ["project_path", "name"],
    "add_wall": ["project_path", "x1", "y1", "x2", "y2"],
    "add_room": ["project_path", "points"],
    "add_furniture": ["project_path", "catalog_id", "x", "y"],
    "add_dimension": ["project_path", "x1", "y1", "x2", "y2"],
    "list_elements": ["project_path"],
    "export_project": ["project_path"],
    "open_reference": ["sample_sh3d_path"],
    "validate_project": ["project_path"],
    "delete_element": ["project_path", "element_id"],
}


def test_server_lists_exact_expected_tools_and_schemas() -> None:
    async def run_check() -> None:
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        assert tool_names == list(EXPECTED_TOOL_REQUIRED_PARAMS)

        tool_by_name = {tool.name: tool for tool in tools}
        for tool_name, required_params in EXPECTED_TOOL_REQUIRED_PARAMS.items():
            schema = tool_by_name[tool_name].input_schema
            assert schema["type"] == "object"
            assert schema["required"] == required_params
            assert set(required_params).issubset(schema["properties"])

    asyncio.run(run_check())
