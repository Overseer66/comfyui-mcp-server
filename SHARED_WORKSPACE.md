# ComfyUI Shared Workspace Guide

## Overview

ComfyUI functions as a **collaborative shared workspace** where multiple clients (browser, MCP/Claude, scripts) interact with the same server in real-time. This provides a CRDT-like experience for AI labeling and landmark preview.

## Architecture: Multi-Client Collaboration

```
┌─────────────────────────────────────────────────────────┐
│  ComfyUI Server (sm3lly.lan:30188) - Single Source of  │
│  Truth with WebSocket Broadcasting                      │
│                                                          │
│  Features:                                              │
│  - Real-time execution broadcast                        │
│  - Shared image gallery                                 │
│  - Persistent workflow history                          │
│  - Queue management                                     │
└────────┬──────────────┬──────────────┬─────────────────┘
         │              │              │
    ┌────▼───┐    ┌────▼────┐   ┌────▼────┐
    │Browser │    │  MCP    │   │ Python  │
    │(Human) │    │(Claude) │   │ Scripts │
    └────────┘    └─────────┘   └─────────┘
    - View        - Automate     - Batch
    - Edit        - Analyze      - Process
    - Inspect     - Assist       - Export
```

## How It Works

### 1. WebSocket Broadcasting

Every action broadcasts to all connected clients:
- **Workflow execution starts** → All clients notified
- **Node completes** → Progress updates broadcast
- **Image generated** → Appears in all browsers
- **Error occurs** → All clients see it

### 2. Shared Image Gallery

ComfyUI maintains a **persistent image gallery**:
- Location: `/root/ComfyUI/output/` (in container)
- Accessible via: `http://sm3lly.lan:30188/view?filename=...`
- **Shared across all clients**
- Images persist until manually deleted

### 3. Queue System

Work queue is visible to all clients:
- See what Claude is executing
- See what browser submitted
- Interrupt or clear queue from any client

## Use Case: Interactive Landmark Preview

### Workflow

1. **Claude executes** landmark detection workflow via MCP
2. **You watch** in browser at http://sm3lly.lan:30188
3. **Real-time feedback**:
   - See each node execute
   - Preview generated images instantly
   - Inspect keypoint annotations
4. **Iterate**: Modify parameters and re-run

### Example: Preview AI Labels

**Terminal (Claude via MCP)**:
```bash
# Claude executes this via MCP
just test-landmark-preview
```

**Browser (You)**:
```
1. Open http://sm3lly.lan:30188
2. Watch the "Queue" section (top right)
3. See nodes execute in real-time
4. Click generated images to inspect
5. View keypoint coordinates and confidence scores
```

**What You See**:
- ✅ Original dog image
- ✅ Keypoints overlaid (nose, eyes, ears, paws, tail)
- ✅ Confidence scores per keypoint
- ✅ Quality metrics (how many keypoints detected, occlusion %)
- ✅ Filtered high-quality results

## ComfyUI "Batteries Included" Features

### Built-in Visualization

ComfyUI provides **zero-code visualization**:

#### 1. Image Preview
Every `SaveImage` node automatically:
- Displays in browser's image gallery
- Shows metadata (dimensions, format)
- Allows zoom/pan
- Provides download button

#### 2. Node Outputs
Click any node to see:
- Output values
- Tensor shapes
- Execution time
- Memory usage

#### 3. Workflow Graph
Visual DAG shows:
- Data flow
- Node dependencies
- Execution order
- Current progress

### Built-in Image Tools

**LoadImage Node**:
- Upload via browser
- Drag-and-drop
- URL import
- File browser

**SaveImage Node**:
- Auto-numbering
- Prefix customization
- Format selection (PNG, JPEG, WebP)
- Metadata embedding

**PreviewImage Node**:
- Non-persistent preview (doesn't save to disk)
- Good for debugging

### Custom Node Capabilities

Your existing custom nodes are **already integrated**:

#### DrawKeypointsNode
```python
inputs = {
    "images": IMAGE_BATCH,
    "annotations": ANNOTATION_SET,
    "radius": 8,              # Keypoint circle size
    "thickness": 3,           # Line thickness
    "show_labels": true,      # Show keypoint names
    "show_confidence": true   # Show confidence scores
}
```

**Output**: Images with keypoints drawn → Automatically visible in browser

#### AnnotationVisualizerNode
```python
inputs = {
    "images": IMAGE_BATCH,
    "annotations": ANNOTATION_SET,
    "color_scheme": "rainbow",  # Different color per keypoint type
    "skeleton": true,           # Draw skeleton connections
    "bbox": true               # Draw bounding boxes
}
```

**Output**: Fully annotated images → Real-time browser preview

#### DatasetPreviewNode
```python
inputs = {
    "dataset_path": "/datasets/AP-10K/ap10k-train.json",
    "num_samples": 16,  # Grid of 16 images
    "shuffle": true
}
```

**Output**: Grid preview of dataset samples → Instant visualization

## Practical Workflows

### Workflow 1: Batch Landmark Preview

**Goal**: Preview AI labels on 100 images, inspect quality

```json
{
  "1_load_batch": {
    "class_type": "AP10KDatasetLoaderNode",
    "inputs": {
      "json_path": "/datasets/AP-10K/ap10k-train.json",
      "split": "train"
    }
  },

  "2_ai_labels": {
    "class_type": "GroundingDINOAnnotatorNode",
    "inputs": {
      "images": ["1_load_batch", 0],
      "text_prompt": "dog keypoints"
    }
  },

  "3_visualize": {
    "class_type": "DrawKeypointsNode",
    "inputs": {
      "images": ["1_load_batch", 0],
      "annotations": ["2_ai_labels", 0]
    }
  },

  "4_preview": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "batch_preview",
      "images": ["3_visualize", 0]
    }
  }
}
```

**Experience**:
- Claude: "I'm executing the batch preview workflow..."
- Browser: See images appear one by one
- You: Click to inspect individual images
- You: Notice some labels are wrong
- You: "Claude, filter out images with confidence < 0.5"
- Claude: Updates workflow and re-runs
- Browser: Refined results appear

### Workflow 2: Compare Multiple AI Annotators

**Goal**: Compare GroundingDINO vs SuperAnimal vs Qwen labels

```json
{
  "1_load": {
    "class_type": "LoadImage",
    "inputs": {"image": "dog_test.jpg"}
  },

  "2a_grounding": {
    "class_type": "GroundingDINOAnnotatorNode",
    "inputs": {"images": ["1_load", 0]}
  },

  "2b_superanimal": {
    "class_type": "SuperAnimalAnnotatorNode",
    "inputs": {"images": ["1_load", 0]}
  },

  "2c_qwen": {
    "class_type": "QwenAnnotatorNode",
    "inputs": {"images": ["1_load", 0]}
  },

  "3a_viz_grounding": {
    "class_type": "DrawKeypointsNode",
    "inputs": {
      "images": ["1_load", 0],
      "annotations": ["2a_grounding", 0]
    }
  },

  "3b_viz_superanimal": {
    "class_type": "DrawKeypointsNode",
    "inputs": {
      "images": ["1_load", 0],
      "annotations": ["2b_superanimal", 0]
    }
  },

  "3c_viz_qwen": {
    "class_type": "DrawKeypointsNode",
    "inputs": {
      "images": ["1_load", 0],
      "annotations": ["2c_qwen", 0]
    }
  },

  "4_save_comparison": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "comparison",
      "images": ["3a_viz_grounding", 0, "3b_viz_superanimal", 0, "3c_viz_qwen", 0]
    }
  }
}
```

**Experience**:
- Browser shows 3 versions side-by-side
- You can zoom in to compare keypoint accuracy
- Click each to see metadata (confidence, model used)
- Decide which annotator is best for your dataset

### Workflow 3: Interactive Quality Filtering

**Goal**: Adjust quality thresholds interactively

```json
{
  "1_load": {...},
  "2_annotate": {...},

  "3_quality_filter": {
    "class_type": "AnnotationQualityFilterNode",
    "inputs": {
      "images": ["1_load", 0],
      "annotations": ["2_annotate", 0],
      "min_visible_keypoints": 10,    // Adjust in browser
      "max_occlusion": 0.5,           // Adjust in browser
      "min_confidence": 0.4           // Adjust in browser
    }
  },

  "4_visualize_passed": {
    "class_type": "DrawKeypointsNode",
    "inputs": {
      "images": ["3_quality_filter", "filtered_images"],
      "annotations": ["3_quality_filter", "filtered_annotations"]
    }
  },

  "5_save": {
    "class_type": "SaveImage",
    "inputs": {
      "images": ["4_visualize_passed", 0]
    }
  }
}
```

**Experience**:
1. Claude executes with initial thresholds
2. Browser shows filtered results
3. You: Double-click `min_visible_keypoints` node in browser
4. You: Change value from 10 → 8
5. You: Click "Queue Prompt" in browser
6. Browser: Re-executes with new threshold
7. You: See updated results immediately
8. Iterate until satisfied

## Advanced: Python Scripting

You can also script the entire workflow and still see results in browser:

```python
# scripts/preview_landmarks.py
import asyncio
from comfyui_mcp_server.src.client.comfyui import ComfyUI

async def preview_dataset():
    """Preview landmarks on entire dataset."""
    comfy = ComfyUI(url="http://sm3lly.lan:30188")

    # Execute workflow
    result = await comfy.process_workflow("landmark_preview", {
        "dataset_path": "/datasets/AP-10K/ap10k-train.json",
        "num_samples": 50
    })

    print(f"✓ Generated {len(result)} previews")
    print("👁️  View at: http://sm3lly.lan:30188")

asyncio.run(preview_dataset())
```

**Run this script** → Images appear in browser automatically!

## State Persistence

### What Persists
- ✅ Generated images (in `/output/`)
- ✅ Uploaded images (in `/input/`)
- ✅ Workflow history (in ComfyUI database)
- ✅ Custom node state

### What Doesn't Persist
- ❌ Queue (cleared on restart)
- ❌ WebSocket connections (reconnect on page refresh)
- ❌ In-memory tensors

### Sharing Images

All clients can access the same images:

```python
# Claude generates this URL via MCP
url = "http://sm3lly.lan:30188/view?filename=landmark_preview_00001.png"

# You can:
# 1. Open in browser
# 2. Download
# 3. Share with team
# 4. Use in reports
```

## Reducing Custom Code

### What You DON'T Need to Code

❌ **Image rendering** → Use `SaveImage` node
❌ **Keypoint visualization** → Use `DrawKeypointsNode`
❌ **Quality metrics UI** → Nodes output stats to browser
❌ **Dataset preview** → Use `DatasetPreviewNode`
❌ **Batch processing UI** → ComfyUI queue handles it
❌ **Progress bars** → ComfyUI shows node-by-node progress
❌ **Error handling UI** → ComfyUI shows errors in browser

### What You DO Need to Code

✅ **Custom annotation logic** (unique algorithms)
✅ **Dataset format parsers** (AP-10K, AWA, etc.)
✅ **Quality metrics** (domain-specific rules)
✅ **Export formats** (YOLO, COCO, etc.)

## Comparison: Traditional vs ComfyUI Approach

### Traditional Approach (Gradio/Streamlit)

```python
# Need to write ALL of this:
import gradio as gr

def process_image(image, threshold):
    # 1. Load image
    # 2. Run detector
    # 3. Draw keypoints
    # 4. Compute metrics
    # 5. Render UI
    # 6. Handle uploads
    # 7. Handle downloads
    return annotated_image, metrics_df

gr.Interface(
    fn=process_image,
    inputs=[gr.Image(), gr.Slider(...)],
    outputs=[gr.Image(), gr.DataFrame()],
    # Need to handle state, caching, etc.
).launch()
```

**Lines of code**: ~200-300

### ComfyUI Approach

```json
{
  "1": {"class_type": "LoadImage", ...},
  "2": {"class_type": "GroundingDINOAnnotatorNode", ...},
  "3": {"class_type": "DrawKeypointsNode", ...},
  "4": {"class_type": "SaveImage", ...}
}
```

**Lines of code**: ~20
**Lines of Python**: 0 (just workflow JSON)

## Testing the Shared Workspace

### Try It Now

1. **Open Browser**: http://sm3lly.lan:30188
2. **Run Test** (in terminal):
   ```bash
   cd /home/brianh/promptexecution/app4dog/pupper-ml-onnx-yolo/comfyui-mcp-server
   uv run --with websocket-client --with python-dotenv --with Pillow \
       python test_shared_workspace.py
   ```
3. **Watch Browser**: See workflow execute in real-time
4. **Click Images**: Inspect generated results

### Expected Experience

**Terminal Output**:
```
🚀 Executing workflow...
👁️  Open http://sm3lly.lan:30188 in your browser to watch!

Parameters: {...}

Executing... (check your browser)

✓ Workflow completed!

Generated images (visible in browser):
  - http://sm3lly.lan:30188/view?filename=ComfyUI_00123.png
```

**Browser Shows**:
- Queue item added
- Node-by-node execution progress
- Generated image appears in gallery
- Click to zoom/inspect

## Summary

### ✅ Yes, It's a Shared Workspace (CRDT-like)

- **Multiple clients** connect to same ComfyUI server
- **Real-time synchronization** via WebSocket
- **Shared state** (images, workflows, queue)
- **Collaborative** (Claude executes, you inspect)

### ✅ Yes, ComfyUI Has "Batteries Included"

- **Image visualization**: Built-in gallery and viewer
- **Keypoint drawing**: `DrawKeypointsNode` (already exists)
- **Quality metrics**: `AnnotationQualityFilterNode` (already exists)
- **Dataset preview**: `DatasetPreviewNode` (already exists)
- **No UI code needed**: Workflows are declarative JSON

### ✅ Perfect for Landmark Preview

Your use case is **exactly** what ComfyUI excels at:
1. Load dataset images
2. Run AI annotators (GroundingDINO, SuperAnimal, etc.)
3. Visualize keypoints
4. Filter by quality
5. Preview in browser (real-time)
6. Export to YOLO format

**Zero custom UI code required** - it's all ComfyUI nodes + browser!

## Next Steps

1. ✅ Test the shared workspace (run `test_shared_workspace.py`)
2. ✅ Open browser and watch workflow execute
3. ✅ Try the `landmark_preview.json` workflow
4. Design custom workflows for your specific labeling needs
5. Use Claude via MCP to automate batch processing

The infrastructure is ready. You just need to:
- Define workflows (JSON)
- Implement custom nodes (Python) for domain-specific logic
- Let ComfyUI handle all visualization/UI automatically
