# Dog Dataset ComfyUI Workflow Architecture

## Project Status

**Current**: 20/42 nodes implemented (48% complete)
**Next Phase**: Phase 5 - Dataset Loaders & Annotation Pipeline
**Goal**: 100% ComfyUI workflow coverage for dog pose estimation

## Architecture Principles

### 1. Node-Based Pipeline
All operations are ComfyUI nodes that can be composed into workflows:
- **Input Nodes**: Load datasets, images, annotations
- **Processing Nodes**: Transform, filter, augment data
- **Teacher Nodes**: Generate annotations (GroundingDINO, SuperAnimal, Qwen)
- **Training Nodes**: Train YOLO models
- **Export Nodes**: Save to YOLO format, ONNX export

### 2. Three-Tier Architecture

```
┌─────────────────────────────────────────────┐
│  ComfyUI Web Interface (sm3lly.lan:30188)  │
│  Visual workflow designer + execution       │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  MCP Server (stdio/SSE transport)           │
│  - Workflow management                      │
│  - Tool exposure to Claude                  │
│  - Kubernetes deployment                    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Custom Node Library (dog_dataset_nodes.py) │
│  - Python implementations                   │
│  - Mounted as ConfigMap in k8s              │
│  - Version controlled in git                │
└─────────────────────────────────────────────┘
```

### 3. Kubernetes as Source of Truth

All capabilities deployed declaratively:
- **Workflows**: JSON files in git → ConfigMap → mounted in pod
- **Custom Nodes**: Python files in git → ConfigMap → mounted in custom_nodes/
- **Models**: PersistentVolume claims for checkpoints
- **Configuration**: Helm values.yaml

## Implemented Nodes (Phases 1-4)

### Phase 1: Training Orchestration (9 nodes)
✅ YOLOTrainerNode, ModelEvaluatorNode, ONNXExporterNode
✅ DatasetSplitterNode, EarlyStoppingNode, LearningRateSchedulerNode
✅ CheckpointManagerNode, TensorBoardLoggerNode, GPUMonitorNode

### Phase 2: Annotation (4 nodes)
✅ GroundingDINOAnnotatorNode - Text-based keypoint detection
✅ DepthEstimationNode - Depth Anything V3
✅ PseudoLabelGeneratorNode - YOLO teacher labels
✅ DepthClusteringNode - Depth-based instance segmentation

### Phase 3: Quality & Export (4 nodes)
✅ AnnotationQualityFilterNode, AnnotationEnsembleNode
✅ YOLOExporterNode, AnnotationVisualizerNode

### Phase 4: Dataset Management (3 nodes)
✅ BatchExportNode, DatasetStatisticsNode, AutoSplitNode

### Existing Nodes (from repository)
✅ DogDetectorNode, CropBatchNode, DogPoseNode
✅ MapKeypointsNode, DrawKeypointsNode, DatasetPreviewNode

**Total**: 20 custom nodes

## Phase 5: Dataset Loaders & Preparation (HIGH PRIORITY)

### 5.1 Dataset Loader Nodes

#### AP10KDatasetLoaderNode
**Purpose**: Load AP-10K dog dataset (794 images, 20 keypoints)
**Source**: `ap10k_dataset_loader.py` (352 lines)

**ComfyUI Workflow**:
```json
{
  "1": {
    "class_type": "AP10KDatasetLoaderNode",
    "inputs": {
      "json_path": "/datasets/AP-10K/annotations/ap10k-train-split1.json",
      "split": "train",
      "species_filter": "dog"
    }
  }
}
```

**Outputs**:
- `IMAGE_BATCH`: Tensor [N, H, W, 3]
- `ANNOTATION_LIST`: List of keypoint annotations
- `DATASET_METADATA`: Dict with statistics

**Implementation Status**: ⚠️ NEEDS CONVERSION
**Complexity**: Medium (JSON parsing, keypoint schema mapping)
**Priority**: HIGH (core dataset)

#### AWADatasetImporterNode
**Purpose**: Import AWA (Animals with Attributes) dataset
**Source**: `create_awa_dataset.py` (397 lines)

**ComfyUI Workflow**:
```json
{
  "2": {
    "class_type": "AWADatasetImporterNode",
    "inputs": {
      "awa_path": "/datasets/AWA2",
      "species_filter": ["dog", "wolf", "coyote"],
      "output_dir": "/datasets/awa_processed"
    }
  }
}
```

**Outputs**:
- `IMAGE_BATCH`: Images
- `METADATA`: Species, attributes
- `IMPORT_STATS`: Import statistics

**Implementation Status**: ⚠️ NEEDS CONVERSION
**Complexity**: Medium
**Priority**: MEDIUM (supplementary dataset)

#### MediaIngestionNode
**Purpose**: Ingest mixed media (images/videos), detect dogs, emit crops
**Source**: `src/dogpose/prepare/ingest_media.py` (200+ lines)

**ComfyUI Workflow**:
```json
{
  "3": {
    "class_type": "MediaIngestionNode",
    "inputs": {
      "media_dir": "/datasets/raw_media",
      "file_patterns": "*.{jpg,png,mp4}",
      "frame_sample_rate": 30,
      "detector_model": "yolo11n.pt",
      "confidence_threshold": 0.5
    }
  },
  "4": {
    "class_type": "DogDetectorNode",
    "inputs": {
      "images": ["3", 0]
    }
  },
  "5": {
    "class_type": "CropBatchNode",
    "inputs": {
      "images": ["3", 0],
      "detections": ["4", 0],
      "target_size": 640
    }
  }
}
```

**Outputs**:
- `IMAGE_BATCH`: Extracted frames
- `CROP_BATCH`: Dog crops
- `DATASET_INDEX`: Metadata for tracking

**Implementation Status**: ⚠️ NEEDS CONVERSION (split into VideoFrameExtractorNode + compose)
**Complexity**: High (video processing)
**Priority**: HIGH (data ingestion pipeline)

### 5.2 Annotation Teacher Nodes

#### SuperAnimalAnnotatorNode
**Purpose**: DeepLabCut SuperAnimal pre-trained model annotation
**Source**: `annotate_superanimal.py` (200+ lines)

**ComfyUI Workflow**:
```json
{
  "6": {
    "class_type": "SuperAnimalAnnotatorNode",
    "inputs": {
      "images": ["5", 0],
      "model_type": "superanimal_quadruped",
      "confidence_threshold": 0.3,
      "device": "cuda"
    }
  }
}
```

**Outputs**:
- `ANNOTATION_SET`: 20-keypoint annotations

**Implementation Status**: ⚠️ NEEDS CONVERSION
**Complexity**: High (DLC integration, model loading)
**Priority**: HIGH (key teacher model)

#### VisionModelAnnotatorNode
**Purpose**: Use vision models (GPT-4V, Claude 3.5 Sonnet) for annotation
**Source**: `annotate_with_vision_model.py` (382 lines)

**ComfyUI Workflow**:
```json
{
  "7": {
    "class_type": "VisionModelAnnotatorNode",
    "inputs": {
      "images": ["5", 0],
      "model_name": "claude-3-5-sonnet-20241022",
      "api_key_env": "ANTHROPIC_API_KEY",
      "keypoint_schema": "superanimal_20pt",
      "prompt_template": "Annotate dog keypoints..."
    }
  }
}
```

**Outputs**:
- `ANNOTATION_SET`: Keypoint annotations from VLM

**Implementation Status**: ⚠️ NEEDS CONVERSION
**Complexity**: Medium (API integration)
**Priority**: MEDIUM (alternative teacher)

#### QwenAnnotatorNode
**Purpose**: Qwen3 VLM for dog pose annotation
**Source**: `annotate_qwen3_fixed.py` + `landmark_detection_qwen.py` (merged)

**ComfyUI Workflow**:
```json
{
  "8": {
    "class_type": "QwenAnnotatorNode",
    "inputs": {
      "images": ["5", 0],
      "model_size": "7b",
      "device": "cuda",
      "use_4bit": true
    }
  }
}
```

**Outputs**:
- `ANNOTATION_SET`: Keypoint annotations

**Implementation Status**: ⚠️ NEEDS CONVERSION
**Complexity**: Medium
**Priority**: MEDIUM (local VLM alternative)

### 5.3 Depth Processing Nodes

#### DepthFilterNode (Multiple Variants)
**Purpose**: Depth-based preprocessing filters
**Source**: `depth_filters.py` (357 lines)

**Sub-nodes**:
- `DepthWeightedRGBNode`: Boost foreground using depth
- `DepthMaskNode`: Binary mask from depth
- `DepthEdgeEnhanceNode`: Enhance edges based on depth gradients
- `DepthGradientNode`: Compute depth gradients

**ComfyUI Workflow**:
```json
{
  "9": {
    "class_type": "DepthEstimationNode",
    "inputs": {
      "images": ["3", 0]
    }
  },
  "10": {
    "class_type": "DepthWeightedRGBNode",
    "inputs": {
      "images": ["3", 0],
      "depth_maps": ["9", 0],
      "foreground_boost": 1.5,
      "background_suppress": 0.3
    }
  }
}
```

**Implementation Status**: ⚠️ NEEDS CONVERSION
**Complexity**: Low (image processing)
**Priority**: MEDIUM (enhancement feature)

## Complete Pipeline Workflow Example

### End-to-End Dog Pose Training Workflow

```json
{
  "comment": "Complete dog pose estimation training pipeline",

  "1_load_dataset": {
    "class_type": "AP10KDatasetLoaderNode",
    "inputs": {
      "json_path": "/datasets/AP-10K/ap10k-train.json",
      "split": "train"
    }
  },

  "2_split_dataset": {
    "class_type": "AutoSplitNode",
    "inputs": {
      "images": ["1_load_dataset", 0],
      "annotations": ["1_load_dataset", 1],
      "train_ratio": 0.7,
      "val_ratio": 0.2,
      "test_ratio": 0.1
    }
  },

  "3_depth_estimation": {
    "class_type": "DepthEstimationNode",
    "inputs": {
      "images": ["2_split_dataset", "train_images"]
    }
  },

  "4_grounding_dino": {
    "class_type": "GroundingDINOAnnotatorNode",
    "inputs": {
      "images": ["2_split_dataset", "train_images"],
      "text_prompt": "dog nose, dog eyes, dog ears, paws",
      "box_threshold": 0.35
    }
  },

  "5_superanimal": {
    "class_type": "SuperAnimalAnnotatorNode",
    "inputs": {
      "images": ["2_split_dataset", "train_images"]
    }
  },

  "6_ensemble": {
    "class_type": "AnnotationEnsembleNode",
    "inputs": {
      "annotations_list": [
        ["4_grounding_dino", 0],
        ["5_superanimal", 0],
        ["1_load_dataset", 1]
      ],
      "weights": [0.3, 0.5, 0.2],
      "min_agreement": 2
    }
  },

  "7_quality_filter": {
    "class_type": "AnnotationQualityFilterNode",
    "inputs": {
      "images": ["2_split_dataset", "train_images"],
      "annotations": ["6_ensemble", 0],
      "min_visible_keypoints": 10,
      "max_occlusion": 0.5
    }
  },

  "8_export": {
    "class_type": "BatchExportNode",
    "inputs": {
      "images": ["7_quality_filter", "filtered_images"],
      "annotations": ["7_quality_filter", "filtered_annotations"],
      "output_dir": "/datasets/yolo_training",
      "split": "train"
    }
  },

  "9_train": {
    "class_type": "YOLOTrainerNode",
    "inputs": {
      "dataset_path": ["8_export", 0],
      "model_size": "n",
      "epochs": 100,
      "imgsz": 640,
      "batch_size": 16,
      "device": "0"
    }
  },

  "10_evaluate": {
    "class_type": "ModelEvaluatorNode",
    "inputs": {
      "model_path": ["9_train", "best_model"],
      "test_images": ["2_split_dataset", "test_images"],
      "test_annotations": ["2_split_dataset", "test_annotations"]
    }
  },

  "11_export_onnx": {
    "class_type": "ONNXExporterNode",
    "inputs": {
      "model_path": ["9_train", "best_model"],
      "output_path": "/models/dog_pose_v1.onnx",
      "imgsz": 640,
      "dynamic": true
    }
  }
}
```

## Deployment Strategy

### 1. Development Workflow

```bash
# Test workflow locally
just test-all

# Validate workflow JSON
just validate-workflows

# Run workflow via MCP
uv run --with mcp --with websocket-client --with python-dotenv \
  mcp run src/server.py -- run_workflow_from_file dog_pose_training.json
```

### 2. Kubernetes Deployment

```bash
# Build and push MCP server with new workflows
git add workflows/dog_pose_training.json
git commit -m "feat: Add complete dog pose training workflow"
git push

# Update submodule in parent repo
cd /home/brianh/promptexecution/app4dog/pupper-ml-onnx-yolo
git submodule update --remote comfyui-mcp-server
git commit -m "chore: Update comfyui-mcp-server with dog pose workflow"

# Helm upgrade (triggers container rebuild via GitHub Actions)
helm upgrade comfyui k8s/helm/comfyui/ \
    --namespace comfy \
    --set mcpServer.image.tag=latest \
    --wait
```

### 3. Custom Node Installation

Custom nodes are mounted as ConfigMap:

```yaml
# k8s/helm/comfyui/templates/configmap-custom-nodes.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: comfyui-custom-nodes
data:
  dog_dataset_nodes.py: |
    {{ .Files.Get "custom_nodes/dog_dataset_nodes.py" | indent 4 }}
```

## Testing Infrastructure

### Unit Tests (per node)

```python
# test_ap10k_loader.py
def test_ap10k_loader():
    node = AP10KDatasetLoaderNode()
    result = node.load_dataset(
        json_path="/datasets/AP-10K/ap10k-train.json",
        split="train",
        species_filter="dog"
    )
    assert result[0] is not None  # images
    assert len(result[1]) > 0     # annotations
```

### Integration Tests (full workflows)

```python
# test_dog_pose_pipeline.py
async def test_dog_pose_pipeline():
    comfy = ComfyUI(url="http://sm3lly.lan:30188")
    result = await comfy.process_workflow(
        "dog_pose_training",
        params={
            "dataset_path": "/datasets/AP-10K/ap10k-train.json",
            "epochs": 1,  # Quick test
        }
    )
    assert "11_export_onnx" in result
```

### Justfile Test Targets

```just
# Test specific workflow
test-dog-pose:
    uv run --with websocket-client --with python-dotenv --with Pillow \
        python test_dog_pose_pipeline.py

# Test all workflows
test-all: test-sdxl test-dog-pose
```

## Next Steps

1. ✅ **Test Infrastructure**: Created (justfile, test_sdxl.py, WORKFLOWS.md)
2. ⚠️ **Phase 5 Nodes**: Convert high-priority loaders and annotators
3. ⚠️ **Create Workflows**: Design JSON workflows for common pipelines
4. ⚠️ **K8s Deployment**: Mount custom nodes via ConfigMap
5. ⚠️ **Documentation**: Complete API docs for each node

## References

- [ComfyUI Conversion Roadmap](../COMFYUI_CONVERSION_ROADMAP.md)
- [Custom Nodes Implementation](../custom_nodes/dog_dataset_nodes.py)
- [Workflow Management](./WORKFLOWS.md)
- [MCP Server README](./README.md)
