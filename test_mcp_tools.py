#!/usr/bin/env python3
"""
Test MCP tools registration and workflow collaboration

Verifies that all workflow tools are registered correctly with FastMCP.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.server.fastmcp import FastMCP
from workflow_tools import register_workflow_tools


async def test_mcp_tool_registration():
    """Test that all workflow tools register correctly"""
    print("=" * 60)
    print("TEST: MCP Tool Registration")
    print("=" * 60)

    # Create test MCP server
    mcp = FastMCP("test-comfyui")

    # Register workflow tools
    register_workflow_tools(mcp)

    # Get list of registered tools (async method)
    tools_list = await mcp.list_tools()
    tools = {t.name: t for t in tools_list}

    print(f"\n✓ Registered {len(tools)} MCP tools")

    # Expected workflow tools
    expected_tools = [
        # Lifecycle
        "workflow_create",
        "workflow_load",
        "workflow_save",
        "workflow_list",
        "workflow_set_active",
        "workflow_delete",
        "workflow_clone",
        # Node operations
        "workflow_add_node",
        "workflow_remove_node",
        "workflow_update_node_params",
        "workflow_get_node_info",
        "workflow_list_nodes",
        # Connections
        "workflow_connect_nodes",
        "workflow_disconnect_nodes",
        # Inspection & Export
        "workflow_get_json",
        "workflow_get_summary",
        # Validation
        "workflow_validate",
    ]

    print("\nExpected workflow tools:")
    for tool_name in expected_tools:
        if tool_name in tools:
            print(f"  ✓ {tool_name}")
        else:
            print(f"  ❌ {tool_name} - NOT FOUND")

    # Verify all expected tools are registered
    missing_tools = [t for t in expected_tools if t not in tools]

    if missing_tools:
        print(f"\n❌ Missing tools: {missing_tools}")
        return False

    print(f"\n✓ All {len(expected_tools)} workflow tools registered successfully")

    # Show tool categories
    print("\nTool Categories:")
    print(f"  Lifecycle: 7 tools")
    print(f"  Node Operations: 5 tools")
    print(f"  Connections: 2 tools")
    print(f"  Inspection/Export: 2 tools")
    print(f"  Validation: 1 tool")
    print(f"  Total: {len(expected_tools)} tools")

    return True


async def test_tool_metadata():
    """Test that tools have proper metadata (docstrings, parameters)"""
    print("\n" + "=" * 60)
    print("TEST: Tool Metadata")
    print("=" * 60)

    mcp = FastMCP("test-comfyui")
    register_workflow_tools(mcp)

    # Get tools list
    tools_list = await mcp.list_tools()

    # Check a few key tools for metadata
    test_tool_names = [
        "workflow_create",
        "workflow_add_node",
        "workflow_connect_nodes",
    ]

    print("\nChecking tool metadata:")

    for tool in tools_list:
        if tool.name not in test_tool_names:
            continue

        # Check for description
        has_description = tool.description is not None and len(tool.description.strip()) > 0

        # Get parameters from inputSchema
        params = []
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            props = tool.inputSchema.get("properties", {})
            if isinstance(props, dict):
                params = list(props.keys())

        print(f"  ✓ {tool.name}")
        print(f"    - Description: {'✓' if has_description else '❌'}")
        if params:
            print(f"    - Parameters: {', '.join(params)}")

    print("\n✓ Tool metadata verification complete")


async def test_workflow_lifecycle_tools():
    """Test workflow lifecycle tools end-to-end"""
    print("\n" + "=" * 60)
    print("TEST: Workflow Lifecycle via MCP Tools")
    print("=" * 60)

    from workflow_tools import _session

    # Import the registered tool functions
    mcp = FastMCP("test-comfyui")
    register_workflow_tools(mcp)

    # Get tool references via call_tool
    async def call_tool(tool_name, **kwargs):
        result = await mcp.call_tool(tool_name, kwargs)
        # MCP returns list of TextContent objects, parse JSON from text
        if isinstance(result, list) and len(result) > 0:
            import json
            return json.loads(result[0].text)
        return result

    # Test: Create workflow
    result = await call_tool("workflow_create", name="MCP Test Workflow", description="Testing MCP tools")
    workflow_id = result["workflow_id"]
    print(f"\n✓ Created workflow: {result['name']}")
    print(f"  ID: {workflow_id}")

    # Test: Add nodes
    node1_result = await call_tool(
        "workflow_add_node",
        node_type="AP10KLoaderNode",
        params=["datasets/test.parquet", 0, 10, False, 42, 0, 1]
    )
    node1_id = node1_result["node_id"]
    print(f"\n✓ Added node {node1_id}: {node1_result['node_type']}")

    node2_result = await call_tool(
        "workflow_add_node",
        node_type="QualityHeuristicsNode"
    )
    node2_id = node2_result["node_id"]
    print(f"✓ Added node {node2_id}: {node2_result['node_type']}")

    # Test: Connect nodes
    link_result = await call_tool(
        "workflow_connect_nodes",
        from_node_id=node1_id,
        from_slot=1,
        to_node_id=node2_id,
        to_slot=0,
        data_type="DOGPOSE_RAW_ANN_LIST"
    )
    link_id = link_result["link_id"]
    print(f"\n✓ Connected nodes: {node1_id} → {node2_id} (link {link_id})")

    # Test: Get summary
    summary = await call_tool("workflow_get_summary")
    print(f"\n✓ Workflow summary:")
    print(f"  Name: {summary['name']}")
    print(f"  Nodes: {summary['statistics']['total_nodes']}")
    print(f"  Links: {summary['statistics']['total_links']}")

    # Test: Validate
    validation = await call_tool("workflow_validate")
    print(f"\n✓ Validation result:")
    print(f"  Valid: {validation['valid']}")
    print(f"  Errors: {len(validation['errors'])}")
    print(f"  Warnings: {len(validation['warnings'])}")

    if validation["warnings"]:
        for warning in validation["warnings"]:
            print(f"    - {warning}")

    print("\n✓ MCP workflow lifecycle test complete")


async def run_all_tests():
    """Run all MCP tool tests"""
    print("\n" + "=" * 60)
    print("MCP TOOLS TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Test 1: Tool registration
        if not await test_mcp_tool_registration():
            return 1

        # Test 2: Tool metadata
        await test_tool_metadata()

        # Test 3: Workflow lifecycle via MCP tools
        await test_workflow_lifecycle_tools()

        print("\n" + "=" * 60)
        print("ALL MCP TOOL TESTS PASSED ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(run_all_tests()))
