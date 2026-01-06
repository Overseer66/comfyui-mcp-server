#!/usr/bin/env python3
"""
Test script for workflow_manager and workflow_tools integration

Tests core workflow manipulation functionality without requiring ComfyUI server.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflow_manager import Workflow, WorkflowSession, Node, Link


def test_workflow_creation():
    """Test basic workflow creation"""
    print("=" * 60)
    print("TEST 1: Workflow Creation")
    print("=" * 60)

    workflow = Workflow(name="Test Pipeline", description="A test workflow")

    assert workflow.name == "Test Pipeline"
    assert workflow.description == "A test workflow"
    assert len(workflow.nodes) == 0
    assert len(workflow.links) == 0

    print("✓ Workflow created successfully")
    print(f"  ID: {workflow.id}")
    print(f"  Name: {workflow.name}")
    print()


def test_node_operations():
    """Test adding, removing, and updating nodes"""
    print("=" * 60)
    print("TEST 2: Node Operations")
    print("=" * 60)

    workflow = Workflow(name="Node Test")

    # Add nodes
    node1_id = workflow.add_node(
        node_type="AP10KLoaderNode",
        pos=(100, 100),
        widgets_values=["datasets/.index/ap10k_train_dogs_only.parquet", 0, 100, False, 42, 0, 1]
    )

    node2_id = workflow.add_node(
        node_type="QualityHeuristicsNode",
        pos=(500, 100)
    )

    node3_id = workflow.add_node(
        node_type="FilterAttributesNode",
        pos=(900, 100),
        widgets_values=["high_quality", 0.8, 0.7]
    )

    assert len(workflow.nodes) == 3
    print(f"✓ Added 3 nodes (IDs: {node1_id}, {node2_id}, {node3_id})")

    # Update node params
    success = workflow.update_node_params(node3_id, ["high_quality", 0.6, 0.7])
    assert success
    assert workflow.nodes[node3_id].widgets_values == ["high_quality", 0.6, 0.7]
    print(f"✓ Updated node {node3_id} parameters")

    # Get node info
    info = workflow.get_node_info(node2_id)
    assert info is not None
    assert info["type"] == "QualityHeuristicsNode"
    print(f"✓ Retrieved node info for {node2_id}")

    # Remove a node
    success = workflow.remove_node(node3_id)
    assert success
    assert len(workflow.nodes) == 2
    print(f"✓ Removed node {node3_id}")
    print()


def test_connections():
    """Test connecting and disconnecting nodes"""
    print("=" * 60)
    print("TEST 3: Node Connections")
    print("=" * 60)

    workflow = Workflow(name="Connection Test")

    # Add nodes
    loader_id = workflow.add_node("AP10KLoaderNode")
    quality_id = workflow.add_node("QualityHeuristicsNode")
    filter_id = workflow.add_node("FilterAttributesNode")

    # Connect loader → quality (annotations)
    link1 = workflow.connect_nodes(
        origin_id=loader_id,
        origin_slot=1,
        target_id=quality_id,
        target_slot=0,
        link_type="DOGPOSE_RAW_ANN_LIST"
    )
    assert link1 is not None
    print(f"✓ Connected loader → quality (link {link1})")

    # Connect loader → quality (images)
    link2 = workflow.connect_nodes(
        origin_id=loader_id,
        origin_slot=0,
        target_id=quality_id,
        target_slot=1,
        link_type="DOGPOSE_IMAGE_LIST"
    )
    assert link2 is not None
    print(f"✓ Connected loader → quality (link {link2})")

    # Connect quality → filter
    link3 = workflow.connect_nodes(
        origin_id=quality_id,
        origin_slot=0,
        target_id=filter_id,
        target_slot=1,
        link_type="DOGPOSE_ATTR_LIST"
    )
    assert link3 is not None
    print(f"✓ Connected quality → filter (link {link3})")

    assert len(workflow.links) == 3
    print(f"✓ Total links: {len(workflow.links)}")

    # Disconnect one link
    success = workflow.disconnect_nodes(link2)
    assert success
    assert len(workflow.links) == 2
    print(f"✓ Disconnected link {link2}")
    print()


def test_workflow_session():
    """Test WorkflowSession multi-workflow management"""
    print("=" * 60)
    print("TEST 4: Workflow Session")
    print("=" * 60)

    session = WorkflowSession()

    # Create workflows
    wf1_id = session.create_workflow("Workflow 1", "First workflow")
    wf2_id = session.create_workflow("Workflow 2", "Second workflow")

    assert len(session.workflows) == 2
    assert session.active_workflow_id == wf1_id  # First created becomes active
    print(f"✓ Created 2 workflows")
    print(f"  Active: {session.active_workflow_id}")

    # Get workflows
    wf1 = session.get_workflow(wf1_id)
    wf2 = session.get_workflow()  # Gets active
    assert wf1 is not None
    assert wf2 is not None
    assert wf1.id == wf2.id  # Both should be the same (active)
    print(f"✓ Retrieved workflows")

    # Switch active
    success = session.set_active(wf2_id)
    assert success
    assert session.active_workflow_id == wf2_id
    print(f"✓ Switched active workflow to {wf2_id}")

    # List workflows
    workflow_list = session.list_workflows()
    assert len(workflow_list) == 2
    assert any(w["is_active"] and w["id"] == wf2_id for w in workflow_list)
    print(f"✓ Listed workflows: {len(workflow_list)}")

    # Delete workflow
    success = session.delete_workflow(wf1_id)
    assert success
    assert len(session.workflows) == 1
    print(f"✓ Deleted workflow {wf1_id}")
    print()


def test_workflow_clone():
    """Test workflow cloning"""
    print("=" * 60)
    print("TEST 5: Workflow Cloning")
    print("=" * 60)

    # Create original workflow
    original = Workflow(name="Original", description="Test workflow")
    original.add_node("AP10KLoaderNode", widgets_values=["dataset.parquet"])
    original.add_node("QualityHeuristicsNode")
    original.connect_nodes(1, 0, 2, 0, "IMAGE")

    # Clone
    cloned = original.clone()

    assert cloned.id != original.id
    assert cloned.name == "Original (Copy)"
    assert len(cloned.nodes) == len(original.nodes)
    assert len(cloned.links) == len(original.links)

    # Modify clone shouldn't affect original
    cloned.add_node("FilterAttributesNode")
    assert len(cloned.nodes) == 3
    assert len(original.nodes) == 2

    print(f"✓ Cloned workflow successfully")
    print(f"  Original ID: {original.id}, Nodes: {len(original.nodes)}")
    print(f"  Cloned ID: {cloned.id}, Nodes: {len(cloned.nodes)}")
    print()


def test_json_export_import():
    """Test JSON export and import"""
    print("=" * 60)
    print("TEST 6: JSON Export/Import")
    print("=" * 60)

    # Create workflow
    workflow = Workflow(name="Export Test", description="Test JSON export")
    loader_id = workflow.add_node("AP10KLoaderNode", pos=(100, 100))
    quality_id = workflow.add_node("QualityHeuristicsNode", pos=(500, 100))
    workflow.connect_nodes(loader_id, 0, quality_id, 0, "IMAGE")

    # Export to JSON
    workflow_json = workflow.to_json()

    assert "nodes" in workflow_json
    assert "links" in workflow_json
    assert "workflow_metadata" in workflow_json
    assert len(workflow_json["nodes"]) == 2
    assert len(workflow_json["links"]) == 1

    print(f"✓ Exported workflow to JSON")
    print(f"  Nodes: {len(workflow_json['nodes'])}")
    print(f"  Links: {len(workflow_json['links'])}")

    # Import from JSON
    imported = Workflow.from_json(workflow_json)

    assert imported.name == "Export Test"
    assert len(imported.nodes) == 2
    assert len(imported.links) == 1

    print(f"✓ Imported workflow from JSON")
    print(f"  Name: {imported.name}")
    print(f"  Nodes: {len(imported.nodes)}")
    print()


def test_workflow_validation():
    """Test workflow validation"""
    print("=" * 60)
    print("TEST 7: Workflow Validation")
    print("=" * 60)

    workflow = Workflow(name="Validation Test")

    # Add nodes but don't connect them all
    node1 = workflow.add_node("AP10KLoaderNode")
    node2 = workflow.add_node("QualityHeuristicsNode")
    node3 = workflow.add_node("FilterAttributesNode")  # Disconnected

    # Only connect 1 → 2
    workflow.connect_nodes(node1, 0, node2, 0, "IMAGE")

    # Check for disconnected nodes
    connected_nodes = set()
    for link in workflow.links.values():
        connected_nodes.add(link.origin_id)
        connected_nodes.add(link.target_id)

    disconnected = set(workflow.nodes.keys()) - connected_nodes

    assert node3 in disconnected
    print(f"✓ Detected disconnected nodes: {list(disconnected)}")

    # Check for unconnected inputs
    unconnected_inputs = []
    for node_id, node in workflow.nodes.items():
        for i, input_slot in enumerate(node.inputs):
            if input_slot.get("link") is None:
                unconnected_inputs.append((node_id, i))

    print(f"✓ Detected unconnected inputs: {len(unconnected_inputs)}")
    print()


def test_file_save_load():
    """Test saving and loading workflows from files"""
    print("=" * 60)
    print("TEST 8: File Save/Load")
    print("=" * 60)

    # Create test output directory
    test_output = Path(__file__).parent / "test_output"
    test_output.mkdir(exist_ok=True)

    # Create and save workflow
    workflow = Workflow(name="File Test", description="Testing file I/O")
    workflow.add_node("AP10KLoaderNode", widgets_values=["test.parquet"])
    workflow.add_node("QualityHeuristicsNode")

    test_file = test_output / "test_workflow.json"
    workflow.save(test_file)

    assert test_file.exists()
    print(f"✓ Saved workflow to {test_file}")

    # Load workflow
    loaded = Workflow.from_file(test_file)

    assert loaded.name == "File Test"
    assert len(loaded.nodes) == 2

    print(f"✓ Loaded workflow from file")
    print(f"  Name: {loaded.name}")
    print(f"  Nodes: {len(loaded.nodes)}")

    # Verify JSON structure
    with open(test_file) as f:
        data = json.load(f)

    assert "workflow_metadata" in data
    assert data["workflow_metadata"]["name"] == "File Test"
    print(f"✓ Verified JSON structure")
    print()


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WORKFLOW MANAGER TEST SUITE")
    print("=" * 60)
    print()

    try:
        test_workflow_creation()
        test_node_operations()
        test_connections()
        test_workflow_session()
        test_workflow_clone()
        test_json_export_import()
        test_workflow_validation()
        test_file_save_load()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
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
    sys.exit(run_all_tests())
