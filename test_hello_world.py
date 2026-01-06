#!/usr/bin/env python3
"""
Test Hello World Node: Execute simple text-to-image workflow via MCP.

This validates the Design → Build → Load → Use workflow from AGENTS.md.
Open http://sm3lly.lan:30188 in browser to see the "Hello World from Sub-Agent!" message.
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from client.comfyui import ComfyUI


async def test_hello_world():
    """Execute the Hello World workflow to display text on ComfyUI dashboard."""
    comfy = ComfyUI(url="http://sm3lly.lan:30188")

    print("=" * 70)
    print("🚀 HELLO WORLD NODE TEST - Design → Build → Load → Use")
    print("=" * 70)
    print("")
    print("👁️  Open http://sm3lly.lan:30188 in your browser to see the result!")
    print("")

    # Parameters for the Hello World node
    params = {
        "message": "Hello World from Sub-Agent!",
        "font_size": 64,
        "width": 1024,
        "height": 512,
        "bg_color": "#2C3E50",  # Dark blue-gray
        "text_color": "#ECF0F1",  # Light gray
    }

    print("Parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    print("")
    print("Executing workflow... (check your browser)")
    print("")

    try:
        # Execute the hello_world workflow
        images = await comfy.process_workflow("hello_world", params, return_url=True)

        print("✓ Workflow completed successfully!")
        print("")
        print("Generated images (visible in browser):")
        for node_id, urls in images.items():
            for idx, url in enumerate(urls):
                print(f"  - {url}")

        print("")
        print("=" * 70)
        print("SUCCESS: Hello World node is working!")
        print("The message should be visible on your ComfyUI dashboard.")
        print("=" * 70)

        return True

    except Exception as e:
        print("")
        print("=" * 70)
        print(f"ERROR: Workflow execution failed")
        print(f"Details: {e}")
        print("=" * 70)
        print("")
        print("Troubleshooting:")
        print("1. Make sure ComfyUI is running at http://sm3lly.lan:30188")
        print("2. Verify HelloWorldNode is registered in custom_nodes/__init__.py")
        print("3. Check ComfyUI logs for custom node loading errors")
        print("4. Restart ComfyUI to reload custom nodes")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_hello_world())
    sys.exit(0 if success else 1)
