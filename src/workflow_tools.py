"""
MCP Tools for Dynamic Workflow Collaboration

Enables AI agents to interactively build, modify, and execute ComfyUI workflows.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from workflow_manager import Workflow, WorkflowSession
from mcp_logger import get_logger

# Global session for workflow management
_session = WorkflowSession()

# Global logger
_log = get_logger()


def register_workflow_tools(mcp: FastMCP) -> None:
    """Register all workflow manipulation tools with MCP server"""

    # ==================== WORKFLOW LIFECYCLE ====================

    @mcp.tool()
    async def workflow_create(
        name: str = "Untitled",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new empty workflow.

        Args:
            name: Workflow name
            description: Workflow description

        Returns:
            Workflow ID and metadata
        """
        workflow_id = _session.create_workflow(name, description)

        _log.info(
            "workflow_create",
            f"Created workflow '{name}'",
            details={"description": description},
            workflow_id=workflow_id
        )

        return {
            "workflow_id": workflow_id,
            "name": name,
            "description": description,
            "status": "created"
        }

    @mcp.tool()
    async def workflow_load(
        path: str,
        set_active: bool = True
    ) -> Dict[str, Any]:
        """
        Load a workflow from JSON file.

        Args:
            path: Path to workflow JSON file
            set_active: Set as active workflow

        Returns:
            Workflow ID and summary
        """
        workflow_id = _session.load_workflow(Path(path))
        workflow = _session.get_workflow(workflow_id)

        if set_active:
            _session.set_active(workflow_id)

        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "num_nodes": len(workflow.nodes),
            "num_links": len(workflow.links),
            "is_active": _session.active_workflow_id == workflow_id
        }

    @mcp.tool()
    async def workflow_save(
        path: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save workflow to JSON file.

        Args:
            path: Output file path
            workflow_id: Workflow to save (active if None)

        Returns:
            Save confirmation
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        workflow.save(Path(path))
        return {
            "status": "saved",
            "path": path,
            "workflow_id": workflow.id,
            "name": workflow.name
        }

    @mcp.tool()
    async def workflow_list() -> Dict[str, List[Dict[str, Any]]]:
        """
        List all workflows in current session.

        Returns:
            List of workflow summaries
        """
        return {"workflows": _session.list_workflows()}

    @mcp.tool()
    async def workflow_set_active(workflow_id: str) -> Dict[str, Any]:
        """
        Set the active workflow for subsequent operations.

        Args:
            workflow_id: Workflow to activate

        Returns:
            Status confirmation
        """
        success = _session.set_active(workflow_id)
        if success:
            return {"status": "active", "workflow_id": workflow_id}
        return {"error": "Workflow not found"}

    @mcp.tool()
    async def workflow_delete(workflow_id: str) -> Dict[str, Any]:
        """
        Delete a workflow from session.

        Args:
            workflow_id: Workflow to delete

        Returns:
            Deletion confirmation
        """
        success = _session.delete_workflow(workflow_id)
        if success:
            return {"status": "deleted", "workflow_id": workflow_id}
        return {"error": "Workflow not found"}

    @mcp.tool()
    async def workflow_clone(
        workflow_id: Optional[str] = None,
        new_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clone a workflow.

        Args:
            workflow_id: Workflow to clone (active if None)
            new_name: Name for cloned workflow

        Returns:
            New workflow ID
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        cloned = workflow.clone()
        if new_name:
            cloned.name = new_name

        _session.workflows[cloned.id] = cloned
        return {
            "workflow_id": cloned.id,
            "name": cloned.name,
            "cloned_from": workflow.id
        }

    # ==================== NODE OPERATIONS ====================

    @mcp.tool()
    async def workflow_add_node(
        node_type: str,
        pos_x: Optional[int] = None,
        pos_y: Optional[int] = None,
        params: Optional[List[Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a node to the workflow.

        Args:
            node_type: ComfyUI node class name (e.g., "AP10KLoaderNode")
            pos_x: X position (auto if None)
            pos_y: Y position (auto if None)
            params: Node parameter values (widgets_values)
            workflow_id: Target workflow (active if None)

        Returns:
            Created node ID and info
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        pos = (pos_x, pos_y) if pos_x is not None and pos_y is not None else None
        node_id = workflow.add_node(
            node_type=node_type,
            pos=pos,
            widgets_values=params or []
        )

        _log.info(
            "workflow_add_node",
            f"Added node {node_id}: {node_type}",
            details={"pos": workflow.nodes[node_id].pos, "num_params": len(params or [])},
            workflow_id=workflow.id
        )

        return {
            "node_id": node_id,
            "node_type": node_type,
            "pos": workflow.nodes[node_id].pos,
            "workflow_id": workflow.id
        }

    @mcp.tool()
    async def workflow_remove_node(
        node_id: int,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove a node and all its connections.

        Args:
            node_id: Node to remove
            workflow_id: Target workflow (active if None)

        Returns:
            Removal confirmation
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        success = workflow.remove_node(node_id)
        if success:
            return {"status": "removed", "node_id": node_id}
        return {"error": "Node not found"}

    @mcp.tool()
    async def workflow_update_node_params(
        node_id: int,
        params: List[Any],
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update node parameters.

        Args:
            node_id: Node to update
            params: New parameter values (widgets_values)
            workflow_id: Target workflow (active if None)

        Returns:
            Update confirmation
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        success = workflow.update_node_params(node_id, params)
        if success:
            return {
                "status": "updated",
                "node_id": node_id,
                "params": params
            }
        return {"error": "Node not found"}

    @mcp.tool()
    async def workflow_get_node_info(
        node_id: int,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a node.

        Args:
            node_id: Node to inspect
            workflow_id: Target workflow (active if None)

        Returns:
            Node details including connections
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        info = workflow.get_node_info(node_id)
        if info:
            return info
        return {"error": "Node not found"}

    @mcp.tool()
    async def workflow_list_nodes(
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all nodes in the workflow.

        Args:
            workflow_id: Target workflow (active if None)

        Returns:
            List of node summaries
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        return {"nodes": workflow.list_nodes()}

    # ==================== CONNECTION OPERATIONS ====================

    @mcp.tool()
    async def workflow_connect_nodes(
        from_node_id: int,
        from_slot: int,
        to_node_id: int,
        to_slot: int,
        data_type: str = "IMAGE",
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect two nodes.

        Args:
            from_node_id: Source node ID
            from_slot: Source output slot (usually 0)
            to_node_id: Target node ID
            to_slot: Target input slot (usually 0)
            data_type: Connection type (IMAGE, DOGPOSE_IMAGE_LIST, etc.)
            workflow_id: Target workflow (active if None)

        Returns:
            Created link ID and details
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        link_id = workflow.connect_nodes(
            origin_id=from_node_id,
            origin_slot=from_slot,
            target_id=to_node_id,
            target_slot=to_slot,
            link_type=data_type
        )

        if link_id:
            _log.info(
                "workflow_connect_nodes",
                f"Connected nodes {from_node_id}:{from_slot} → {to_node_id}:{to_slot}",
                details={"link_id": link_id, "type": data_type},
                workflow_id=workflow.id
            )

            return {
                "link_id": link_id,
                "from_node": from_node_id,
                "to_node": to_node_id,
                "type": data_type
            }

        _log.error(
            "workflow_connect_nodes",
            f"Failed to connect {from_node_id} → {to_node_id}",
            details={"from_slot": from_slot, "to_slot": to_slot, "type": data_type},
            workflow_id=workflow.id
        )
        return {"error": "Connection failed (check node IDs and slots)"}

    @mcp.tool()
    async def workflow_disconnect_nodes(
        link_id: int,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove a connection between nodes.

        Args:
            link_id: Link to remove
            workflow_id: Target workflow (active if None)

        Returns:
            Disconnection confirmation
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        success = workflow.disconnect_nodes(link_id)
        if success:
            return {"status": "disconnected", "link_id": link_id}
        return {"error": "Link not found"}

    # ==================== INSPECTION & EXPORT ====================

    @mcp.tool()
    async def workflow_get_json(
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the complete workflow as ComfyUI JSON.

        Args:
            workflow_id: Target workflow (active if None)

        Returns:
            Full workflow JSON
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        return workflow.to_json()

    @mcp.tool()
    async def workflow_get_summary(
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a human-readable summary of the workflow.

        Args:
            workflow_id: Target workflow (active if None)

        Returns:
            Workflow summary with statistics
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        # Build connection map
        connections = []
        for link in workflow.links.values():
            origin_node = workflow.nodes[link.origin_id]
            target_node = workflow.nodes[link.target_id]
            connections.append({
                "from": f"{origin_node.type} (#{link.origin_id})",
                "to": f"{target_node.type} (#{link.target_id})",
                "type": link.type
            })

        # Node type counts
        node_types = {}
        for node in workflow.nodes.values():
            node_types[node.type] = node_types.get(node.type, 0) + 1

        return {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "statistics": {
                "total_nodes": len(workflow.nodes),
                "total_links": len(workflow.links),
                "node_types": node_types
            },
            "nodes": workflow.list_nodes(),
            "connections": connections
        }

    # ==================== VALIDATION ====================

    @mcp.tool()
    async def workflow_validate(
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate workflow for common issues.

        Args:
            workflow_id: Target workflow (active if None)

        Returns:
            Validation results with warnings/errors
        """
        workflow = _session.get_workflow(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        issues = []
        warnings = []

        # Check for disconnected nodes
        connected_nodes = set()
        for link in workflow.links.values():
            connected_nodes.add(link.origin_id)
            connected_nodes.add(link.target_id)

        disconnected = set(workflow.nodes.keys()) - connected_nodes
        if disconnected:
            warnings.append(f"Disconnected nodes: {list(disconnected)}")

        # Check for cycles (simple detection)
        # TODO: Implement proper cycle detection algorithm

        # Check for missing inputs
        for node_id, node in workflow.nodes.items():
            for i, input_slot in enumerate(node.inputs):
                if input_slot.get("link") is None:
                    warnings.append(
                        f"Node {node_id} ({node.type}) has unconnected input slot {i}"
                    )

        return {
            "valid": len(issues) == 0,
            "errors": issues,
            "warnings": warnings,
            "num_nodes": len(workflow.nodes),
            "num_links": len(workflow.links)
        }
