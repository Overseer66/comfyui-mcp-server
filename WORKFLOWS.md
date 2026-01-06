# ComfyUI Workflow Management

## Overview

This document describes the declarative workflow management approach for ComfyUI integration with MCP server.

## Principles

1. **K8s as Source of Truth**: All capabilities are deployed via Kubernetes manifests
2. **Idempotent Operations**: All operations can be run repeatedly without side effects
3. **Declarative Configuration**: Workflows are defined as JSON files, not CLI operations
4. **Version Control**: Only idempotent capabilities are version controlled

## Workflow Directory Structure

```
workflows/
├── text_to_image.json       # Original SD 1.5 workflow (deprecated)
├── text_to_image_sdxl.json  # SDXL-compatible workflow (active)
└── custom/                  # Custom workflows for dog dataset project
    └── (future workflows)
```

## Testing Infrastructure

### Running Tests

```bash
# Test SDXL workflow
just test-sdxl

# Test all workflows
just test-all

# Validate workflow JSON syntax
just validate-workflows
```

### Querying ComfyUI

```bash
# Check available models
just query-models

# Check system info (GPU, memory, etc.)
just query-system
```

## Creating New Workflows

### 1. Query Available Resources

Before creating a workflow, check what models and nodes are available:

```bash
# Check available checkpoint models
just query-models

# Get full node/model catalog
curl -s http://sm3lly.lan:30188/object_info | jq 'keys'
```

### 2. Design Workflow in ComfyUI UI

1. Access ComfyUI web interface: http://sm3lly.lan:30188
2. Build your workflow visually
3. Export as JSON via "Save (API Format)" button

### 3. Add to Workflows Directory

```bash
# Save exported workflow
cp ~/Downloads/workflow_api.json workflows/my_custom_workflow.json

# Validate JSON
just validate-workflows
```

### 4. Create Test

```python
# Example test: test_my_workflow.py
import asyncio
from client.comfyui import ComfyUI

async def test_my_workflow():
    comfy = ComfyUI(url=f'http://sm3lly.lan:30188')
    params = {
        "text": "test prompt",
        "seed": 42,
    }
    images = await comfy.process_workflow("my_custom_workflow", params)
    assert len(images) > 0
    print("✓ Test passed")

asyncio.run(test_my_workflow())
```

### 5. Add to Test Suite

Add test target to `justfile`:

```just
test-my-workflow:
    uv run --with websocket-client --with python-dotenv --with Pillow python test_my_workflow.py

test-all: test-sdxl test-my-workflow
```

## Workflow Compatibility

### Current Environment

- **ComfyUI Version**: 0.3.75
- **Available Models**:
  - `sd_xl_base_1.0.safetensors` (SDXL 1.0)
- **GPU**: NVIDIA GeForce RTX 3090 (24GB VRAM)
- **Python**: 3.11.13
- **PyTorch**: 2.8.0+cu128

### Model Requirements

Different models require different latent image sizes:

- **SD 1.5**: 512x512 (not available)
- **SDXL**: 1024x1024 (available)

## Dog Dataset Project Integration

### Phase 1: Completed Nodes (20/42)

The following ComfyUI workflows need to be created for the dog dataset project:

#### Data Loading Nodes
- Load Dog Images
- Load Annotations
- Load Dataset Split

#### Preprocessing Nodes
- Resize Images
- Normalize Images
- Augment Images (flip, rotate, crop)

#### Training Nodes
- YOLO Training Loop
- Loss Calculation
- Gradient Update

#### Evaluation Nodes
- Run Inference
- Calculate mAP
- Visualize Results

### Phase 2: Remaining Nodes (22/42)

To be designed based on project requirements.

## Deployment to Kubernetes

Workflows are automatically available in the MCP server container when:

1. Workflow JSON is added to `workflows/` directory
2. Changes are committed to git
3. Submodule is updated in parent repo
4. Container is rebuilt and pushed to ghcr.io
5. Helm chart is upgraded:

```bash
helm upgrade comfyui k8s/helm/comfyui/ \
    --namespace comfy \
    --set mcpServer.image.tag=latest
```

## MCP Server Integration

The MCP server automatically discovers workflows in the `workflows/` directory and exposes them as tools:

- `run_workflow_from_file(file_path)` - Run workflow from file path
- `run_workflow_from_json(json_data)` - Run workflow from JSON data
- `text_to_image(...)` - Built-in SDXL text-to-image tool

## References

- [ComfyUI API Documentation](https://docs.comfy.org/)
- [MCP Server README](./README.md)
- [Project Documentation](../README.md)
