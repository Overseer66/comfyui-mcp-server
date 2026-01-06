#!/usr/bin/env python3
"""
Test ComfyUI SDXL workflow connectivity.
This is an idempotent test that verifies:
1. ComfyUI server is accessible
2. SDXL model is available
3. Workflow can execute successfully
4. Images can be generated and retrieved
"""
import asyncio
import os
import io
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from client.comfyui import ComfyUI
from PIL import Image


async def test_sdxl_workflow():
    """Test SDXL workflow execution."""
    # ComfyUI connection from environment
    comfy = ComfyUI(
        url=f'http://{os.environ.get("COMFYUI_HOST", "localhost")}:{os.environ.get("COMFYUI_PORT", "8188")}'
    )

    # Test parameters
    params = {
        "text": "A cute puppy playing in a garden, highly detailed, 4k",
        "seed": 42,
        "steps": 20,
        "cfg": 8.0,
        "denoise": 1.0,
    }

    print(f"Testing ComfyUI at {comfy.url}")
    print(f"Workflow: text_to_image_sdxl")
    print(f"Parameters: {params}")

    try:
        # Execute workflow
        print("\nExecuting workflow...")
        images = await comfy.process_workflow("text_to_image_sdxl", params, return_url=False)

        # Process results
        total_images = sum(len(node_images) for node_images in images.values())
        print(f"✓ Generated {total_images} image(s)")

        # Create test output directory
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)

        # Save images
        for node_id, node_images in images.items():
            print(f"\n✓ Node {node_id} generated {len(node_images)} image(s)")
            for idx, image_data in enumerate(node_images):
                # Convert bytes to PIL Image
                image = Image.open(io.BytesIO(image_data))
                print(f"  - Image {idx + 1}: {image.size[0]}x{image.size[1]} pixels")

                # Save to test_output directory
                save_path = output_dir / f"sdxl_test_{node_id}_{idx}.png"
                image.save(save_path)
                print(f"  - Saved: {save_path}")

        print("\n✓ Test PASSED: SDXL workflow executed successfully")
        return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sdxl_workflow())
    sys.exit(0 if success else 1)
