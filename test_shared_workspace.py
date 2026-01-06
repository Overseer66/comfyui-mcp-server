#!/usr/bin/env python3
"""
Test shared workspace: Execute workflow via MCP while browser watches.
Open http://sm3lly.lan:30188 in browser to see real-time execution.
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from client.comfyui import ComfyUI

async def test_shared_execution():
    """Execute a workflow that the browser can watch in real-time."""
    comfy = ComfyUI(url="http://sm3lly.lan:30188")
    
    print("🚀 Executing workflow...")
    print("👁️  Open http://sm3lly.lan:30188 in your browser to watch!")
    print("")
    
    params = {
        "text": "A golden retriever puppy with visible keypoints, anatomical diagram style",
        "seed": 12345,
        "steps": 15,
        "cfg": 7.5,
        "denoise": 1.0,
    }
    
    print(f"Parameters: {params}")
    print("\nExecuting... (check your browser)")
    
    # This will show up in the browser's queue and execution log
    images = await comfy.process_workflow("text_to_image_sdxl", params, return_url=True)
    
    print("\n✓ Workflow completed!")
    print("\nGenerated images (visible in browser):")
    for node_id, urls in images.items():
        for idx, url in enumerate(urls):
            print(f"  - {url}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_shared_execution())
