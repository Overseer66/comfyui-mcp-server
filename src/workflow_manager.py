"""
Dynamic Workflow Manager for ComfyUI MCP Integration

Enables AI agents to load, inspect, mutate, and execute ComfyUI workflows in memory.
Supports collaborative workflow construction with type safety and validation.
"""

import copy
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from client.comfyui import ComfyUI


@dataclass
class Node:
    """Represents a node in a ComfyUI workflow"""
    id: int
    type: str
    pos: Tuple[int, int]
    size: Tuple[int, int]
    flags: Dict[str, Any] = field(default_factory=dict)
    order: int = 0
    mode: int = 0
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    widgets_values: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to ComfyUI JSON format"""
        return {
            "id": self.id,
            "type": self.type,
            "pos": list(self.pos),
            "size": list(self.size),
            "flags": self.flags,
            "order": self.order,
            "mode": self.mode,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "properties": self.properties,
            "widgets_values": self.widgets_values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        """Create node from ComfyUI JSON format"""
        return cls(
            id=data["id"],
            type=data["type"],
            pos=tuple(data["pos"]),
            size=tuple(data["size"]),
            flags=data.get("flags", {}),
            order=data.get("order", 0),
            mode=data.get("mode", 0),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            properties=data.get("properties", {}),
            widgets_values=data.get("widgets_values", [])
        )


@dataclass
class Link:
    """Represents a connection between nodes"""
    id: int
    origin_id: int
    origin_slot: int
    target_id: int
    target_slot: int
    type: str

    def to_list(self) -> List[Any]:
        """Convert link to ComfyUI JSON format"""
        return [self.id, self.origin_id, self.origin_slot,
                self.target_id, self.target_slot, self.type]

    @classmethod
    def from_list(cls, data: List[Any]) -> "Link":
        """Create link from ComfyUI JSON format"""
        return cls(
            id=data[0],
            origin_id=data[1],
            origin_slot=data[2],
            target_id=data[3],
            target_slot=data[4],
            type=data[5]
        )


@dataclass
class WorkflowGroup:
    """Represents a visual grouping of nodes"""
    title: str
    bounding: List[int]
    color: str
    font_size: int = 24


class Workflow:
    """In-memory representation of a ComfyUI workflow with mutation support"""

    def __init__(self, name: str = "Untitled", description: str = ""):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.nodes: Dict[int, Node] = {}
        self.links: Dict[int, Link] = {}
        self.groups: List[WorkflowGroup] = []
        self.config: Dict[str, Any] = {}
        self.extra: Dict[str, Any] = {"ds": {"scale": 1.0, "offset": [0, 0]}}
        self.version = 0.4
        self.metadata: Dict[str, Any] = {
            "created_with": "comfyui-mcp",
            "agent": "claude",
            "version": "1.0.0"
        }
        self._next_node_id = 1
        self._next_link_id = 1

    def add_node(
        self,
        node_type: str,
        pos: Optional[Tuple[int, int]] = None,
        widgets_values: Optional[List[Any]] = None,
        **kwargs
    ) -> int:
        """
        Add a node to the workflow.

        Args:
            node_type: The ComfyUI node class name
            pos: (x, y) position, auto-calculated if None
            widgets_values: Node parameter values
            **kwargs: Additional node properties

        Returns:
            node_id: The ID of the created node
        """
        node_id = self._next_node_id
        self._next_node_id += 1

        # Auto-position if not provided
        if pos is None:
            pos = self._auto_position(node_id)

        node = Node(
            id=node_id,
            type=node_type,
            pos=pos,
            size=(320, 240),  # Default size
            widgets_values=widgets_values or [],
            **kwargs
        )

        self.nodes[node_id] = node
        return node_id

    def remove_node(self, node_id: int) -> bool:
        """
        Remove a node and all its connections.

        Args:
            node_id: The node to remove

        Returns:
            True if node was removed, False if not found
        """
        if node_id not in self.nodes:
            return False

        # Remove all links connected to this node
        links_to_remove = []
        for link_id, link in self.links.items():
            if link.origin_id == node_id or link.target_id == node_id:
                links_to_remove.append(link_id)

        for link_id in links_to_remove:
            del self.links[link_id]

        # Remove the node
        del self.nodes[node_id]
        return True

    def connect_nodes(
        self,
        origin_id: int,
        origin_slot: int,
        target_id: int,
        target_slot: int,
        link_type: str = "IMAGE"
    ) -> Optional[int]:
        """
        Connect two nodes.

        Args:
            origin_id: Source node ID
            origin_slot: Source output slot index
            target_id: Target node ID
            target_slot: Target input slot index
            link_type: Data type being passed

        Returns:
            link_id if successful, None if validation fails
        """
        # Validate nodes exist
        if origin_id not in self.nodes or target_id not in self.nodes:
            return None

        link_id = self._next_link_id
        self._next_link_id += 1

        link = Link(
            id=link_id,
            origin_id=origin_id,
            origin_slot=origin_slot,
            target_id=target_id,
            target_slot=target_slot,
            type=link_type
        )

        self.links[link_id] = link

        # Update node input/output references
        origin_node = self.nodes[origin_id]
        target_node = self.nodes[target_id]

        # Ensure outputs list is long enough
        while len(origin_node.outputs) <= origin_slot:
            origin_node.outputs.append({
                "name": f"output_{len(origin_node.outputs)}",
                "type": link_type,
                "links": [],
                "shape": 3
            })

        # Add link to origin output
        if "links" not in origin_node.outputs[origin_slot]:
            origin_node.outputs[origin_slot]["links"] = []
        origin_node.outputs[origin_slot]["links"].append(link_id)

        # Ensure inputs list is long enough
        while len(target_node.inputs) <= target_slot:
            target_node.inputs.append({
                "name": f"input_{len(target_node.inputs)}",
                "type": link_type,
                "link": None
            })

        # Set link on target input
        target_node.inputs[target_slot]["link"] = link_id

        return link_id

    def disconnect_nodes(self, link_id: int) -> bool:
        """
        Remove a connection between nodes.

        Args:
            link_id: The link to remove

        Returns:
            True if link was removed, False if not found
        """
        if link_id not in self.links:
            return False

        link = self.links[link_id]

        # Update origin node outputs
        if link.origin_id in self.nodes:
            origin_node = self.nodes[link.origin_id]
            if link.origin_slot < len(origin_node.outputs):
                output = origin_node.outputs[link.origin_slot]
                if "links" in output and link_id in output["links"]:
                    output["links"].remove(link_id)

        # Update target node inputs
        if link.target_id in self.nodes:
            target_node = self.nodes[link.target_id]
            if link.target_slot < len(target_node.inputs):
                target_node.inputs[link.target_slot]["link"] = None

        del self.links[link_id]
        return True

    def update_node_params(self, node_id: int, widgets_values: List[Any]) -> bool:
        """
        Update node parameters.

        Args:
            node_id: Node to update
            widgets_values: New parameter values

        Returns:
            True if successful, False if node not found
        """
        if node_id not in self.nodes:
            return False

        self.nodes[node_id].widgets_values = widgets_values
        return True

    def get_node_info(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a node"""
        if node_id not in self.nodes:
            return None

        node = self.nodes[node_id]
        connected_to = []
        connected_from = []

        for link in self.links.values():
            if link.origin_id == node_id:
                connected_to.append({
                    "node_id": link.target_id,
                    "node_type": self.nodes[link.target_id].type,
                    "from_slot": link.origin_slot,
                    "to_slot": link.target_slot
                })
            if link.target_id == node_id:
                connected_from.append({
                    "node_id": link.origin_id,
                    "node_type": self.nodes[link.origin_id].type,
                    "from_slot": link.origin_slot,
                    "to_slot": link.target_slot
                })

        return {
            "id": node.id,
            "type": node.type,
            "pos": node.pos,
            "widgets_values": node.widgets_values,
            "connected_to": connected_to,
            "connected_from": connected_from
        }

    def list_nodes(self) -> List[Dict[str, Any]]:
        """Get summary of all nodes"""
        return [
            {
                "id": node.id,
                "type": node.type,
                "pos": node.pos,
                "num_inputs": len(node.inputs),
                "num_outputs": len(node.outputs)
            }
            for node in self.nodes.values()
        ]

    def to_json(self) -> Dict[str, Any]:
        """Export workflow to ComfyUI JSON format"""
        return {
            "last_node_id": self._next_node_id - 1,
            "last_link_id": self._next_link_id - 1,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "links": [link.to_list() for link in self.links.values()],
            "groups": [
                {
                    "title": g.title,
                    "bounding": g.bounding,
                    "color": g.color,
                    "font_size": g.font_size
                }
                for g in self.groups
            ],
            "config": self.config,
            "extra": self.extra,
            "version": self.version,
            "workflow_metadata": {
                **self.metadata,
                "name": self.name,
                "description": self.description
            }
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Workflow":
        """Load workflow from ComfyUI JSON format"""
        metadata = data.get("workflow_metadata", {})
        workflow = cls(
            name=metadata.get("name", "Imported Workflow"),
            description=metadata.get("description", "")
        )

        # Load nodes
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            workflow.nodes[node.id] = node
            workflow._next_node_id = max(workflow._next_node_id, node.id + 1)

        # Load links
        for link_data in data.get("links", []):
            link = Link.from_list(link_data)
            workflow.links[link.id] = link
            workflow._next_link_id = max(workflow._next_link_id, link.id + 1)

        # Load groups
        for group_data in data.get("groups", []):
            workflow.groups.append(WorkflowGroup(**group_data))

        workflow.config = data.get("config", {})
        workflow.extra = data.get("extra", {})
        workflow.version = data.get("version", 0.4)
        workflow.metadata = metadata

        return workflow

    @classmethod
    def from_file(cls, path: Path) -> "Workflow":
        """Load workflow from JSON file"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_json(data)

    def save(self, path: Path) -> None:
        """Save workflow to JSON file"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f, indent=2)

    def clone(self) -> "Workflow":
        """Create a deep copy of the workflow"""
        cloned = Workflow(name=f"{self.name} (Copy)", description=self.description)
        cloned.nodes = {k: copy.deepcopy(v) for k, v in self.nodes.items()}
        cloned.links = {k: copy.deepcopy(v) for k, v in self.links.items()}
        cloned.groups = copy.deepcopy(self.groups)
        cloned.config = copy.deepcopy(self.config)
        cloned.extra = copy.deepcopy(self.extra)
        cloned.metadata = copy.deepcopy(self.metadata)
        cloned._next_node_id = self._next_node_id
        cloned._next_link_id = self._next_link_id
        return cloned

    def _auto_position(self, node_id: int) -> Tuple[int, int]:
        """Calculate auto-position for a new node"""
        if not self.nodes:
            return (50, 50)

        # Place new nodes to the right of existing nodes
        max_x = max(node.pos[0] for node in self.nodes.values())
        max_y = max(node.pos[1] for node in self.nodes.values())

        # Simple grid layout
        column = (node_id - 1) % 3
        row = (node_id - 1) // 3

        return (50 + column * 400, 50 + row * 300)


class WorkflowSession:
    """Manages multiple workflows in a collaborative session"""

    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflow_id: Optional[str] = None

    def create_workflow(self, name: str = "Untitled", description: str = "") -> str:
        """Create a new workflow and return its ID"""
        workflow = Workflow(name=name, description=description)
        self.workflows[workflow.id] = workflow
        if self.active_workflow_id is None:
            self.active_workflow_id = workflow.id
        return workflow.id

    def load_workflow(self, path: Path) -> str:
        """Load workflow from file and return its ID"""
        workflow = Workflow.from_file(path)
        self.workflows[workflow.id] = workflow
        if self.active_workflow_id is None:
            self.active_workflow_id = workflow.id
        return workflow.id

    def get_workflow(self, workflow_id: Optional[str] = None) -> Optional[Workflow]:
        """Get workflow by ID, or active workflow if None"""
        if workflow_id is None:
            workflow_id = self.active_workflow_id
        return self.workflows.get(workflow_id) if workflow_id else None

    def set_active(self, workflow_id: str) -> bool:
        """Set the active workflow"""
        if workflow_id in self.workflows:
            self.active_workflow_id = workflow_id
            return True
        return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            if self.active_workflow_id == workflow_id:
                self.active_workflow_id = next(iter(self.workflows.keys()), None)
            return True
        return False

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows in session"""
        return [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "num_nodes": len(wf.nodes),
                "num_links": len(wf.links),
                "is_active": wf.id == self.active_workflow_id
            }
            for wf in self.workflows.values()
        ]
