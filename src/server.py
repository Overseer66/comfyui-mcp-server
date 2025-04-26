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

if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))
