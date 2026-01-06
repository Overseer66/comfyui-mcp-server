import os
import json
import urllib.request
import urllib.parse
from typing import Any
from client.comfyui import ComfyUI
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("comfyui")

# Import workflow collaboration tools
try:
    from workflow_tools import register_workflow_tools
    WORKFLOW_TOOLS_AVAILABLE = True
except ImportError:
    WORKFLOW_TOOLS_AVAILABLE = False

# Import MCP logger
try:
    from mcp_logger import get_logger
    MCP_LOGGER_AVAILABLE = True
    _mcp_log = get_logger()
except ImportError:
    MCP_LOGGER_AVAILABLE = False
    _mcp_log = None

@mcp.tool()
async def text_to_image(prompt: str, seed: int, steps: int, cfg: float, denoise: float) -> Any:
    """Generate an image from a prompt.
    
    Args:
        prompt: The prompt to generate the image from.
        seed: The seed to use for the image generation.
        steps: The number of steps to use for the image generation.
        cfg: The CFG scale to use for the image generation.
        denoise: The denoise strength to use for the image generation.
    """
    auth = os.environ.get("COMFYUI_AUTHENTICATION")
    comfy = ComfyUI(
        url=f'http://{os.environ.get("COMFYUI_HOST", "localhost")}:{os.environ.get("COMFYUI_PORT", 8188)}',
        authentication=auth
    )
    images = await comfy.process_workflow("text_to_image", {"prompt": prompt, "seed": seed, "steps": steps, "cfg": cfg, "denoise": denoise}, return_url=os.environ.get("RETURN_URL", "true").lower() == "true")
    return images

@mcp.tool()
async def download_image(url: str, save_path: str) -> Any:
    """Download an image from a URL and save it to a file.
    
    Args:
        url: The URL of the image to download.
        save_path: The absolute path to save the image to. Must be an absolute path, otherwise the image will be saved relative to the server location.
    """
    urllib.request.urlretrieve(url, save_path)
    return {"success": True}

@mcp.tool()
async def run_workflow_from_file(file_path: str) -> Any:
    """Run a workflow from a file.
    
    Args:
        file_path: The absolute path to the file to run.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    
    auth = os.environ.get("COMFYUI_AUTHENTICATION")
    comfy = ComfyUI(
        url=f'http://{os.environ.get("COMFYUI_HOST", "localhost")}:{os.environ.get("COMFYUI_PORT", 8188)}',
        authentication=auth
    )
    images = await comfy.process_workflow(workflow, {}, return_url=os.environ.get("RETURN_URL", "true").lower() == "true")
    return images

@mcp.tool()
async def run_workflow_from_json(json_data: dict) -> Any:
    """Run a workflow from a JSON data.
    
    Args:
        json_data: The JSON data to run.
    """
    workflow = json_data
    
    auth = os.environ.get("COMFYUI_AUTHENTICATION")
    comfy = ComfyUI(
        url=f'http://{os.environ.get("COMFYUI_HOST", "localhost")}:{os.environ.get("COMFYUI_PORT", 8188)}',
        authentication=auth
    )
    images = await comfy.process_workflow(workflow, {}, return_url=os.environ.get("RETURN_URL", "true").lower() == "true")
    return images

# MCP Log Query Tools
if MCP_LOGGER_AVAILABLE:
    @mcp.tool()
    async def mcp_get_logs(
        count: int = 100,
        level: str = None,
        workflow_id: str = None
    ) -> Any:
        """Get recent MCP workflow operation logs.

        Args:
            count: Maximum number of log entries to return (default: 100)
            level: Filter by log level (debug, info, warning, error). None = all levels
            workflow_id: Filter by workflow ID. None = all workflows

        Returns:
            List of log entries with timestamps and details
        """
        from mcp_logger import LogLevel

        level_enum = None
        if level:
            level_enum = LogLevel(level.lower())

        logs = _mcp_log.get_recent(count=count, level=level_enum, workflow_id=workflow_id)
        return {"logs": logs, "count": len(logs)}

    @mcp.tool()
    async def mcp_get_all_logs() -> Any:
        """Get all MCP logs in the buffer.

        Returns:
            All log entries currently in the circular buffer
        """
        logs = _mcp_log.get_all()
        return {"logs": logs, "count": len(logs)}

    @mcp.tool()
    async def mcp_get_log_stats() -> Any:
        """Get MCP logging statistics.

        Returns:
            Statistics about log entries (counts by level, by operation, etc.)
        """
        return _mcp_log.get_stats()

    @mcp.tool()
    async def mcp_clear_logs() -> Any:
        """Clear all MCP logs from the buffer.

        Returns:
            Confirmation message
        """
        _mcp_log.clear()
        return {"status": "cleared", "message": "All MCP logs cleared"}

# Register dynamic workflow collaboration tools
if WORKFLOW_TOOLS_AVAILABLE:
    register_workflow_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))
