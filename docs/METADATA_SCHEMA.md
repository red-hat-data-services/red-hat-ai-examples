# Example Metadata Schema

Every example in the red-hat-ai-examples repository MUST include an `example.yaml` metadata file. This file provides structured information about the example, enabling discovery, validation, and documentation generation.

---

## Schema Definition

```yaml
metadata:
  # Basic Information
  title: string                        # Human-readable title
  description: string                  # 2-3 sentence description
  status: community | validated        # Validation status

  # Hardware Requirements (Optional)
  hardware:
    gpu:
      required: boolean                # Whether GPU is required
      type: string | null              # e.g., "NVIDIA L40S", "A10"
      count: integer | null            # Number of GPUs needed
      memory_per_gpu: string | null    # e.g., "48GB", "24GB"
    cpu:
      cores: integer | null            # CPU cores required
    memory: string | null              # System memory (e.g., "32Gi")
    storage: string | null             # Storage needed (e.g., "10Gi RWX")
    multi_node: boolean                # Multi-node setup required

  # Time Estimates (Optional)
  duration_estimate:
    setup: string | null               # e.g., "15 minutes"
    execution: string                  # e.g., "2 hours"
    total: string                      # Total time

  # Classification (Optional)
  tags: list[string]                   # From predefined list
  use_case: string                     # From predefined list
  complexity: beginner | intermediate | advanced

  # Components
  components:
    rhoai: list[string]                # RHOAI components (from predefined list)
    external: list[string] | null      # External services (optional)
```

---

## Required Fields

All metadata files MUST include:

- `metadata.title`
- `metadata.description`
- `metadata.status`
- `metadata.components.rhoai` (at least one component)

---

## Field Descriptions

### Basic Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Human-readable title (under 80 characters) |
| `description` | string | Yes | 2-3 sentence description of the example |
| `status` | enum | Yes | `community` or `validated` |

### Hardware Requirements

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hardware.gpu.required` | boolean | No* | Whether GPU is required |
| `hardware.gpu.type` | string | No | GPU type (e.g., "NVIDIA L40S") |
| `hardware.gpu.count` | integer | No | Number of GPUs needed |
| `hardware.gpu.memory_per_gpu` | string | No | Memory per GPU (e.g., "48GB") |
| `hardware.cpu.cores` | integer | No | CPU cores required |
| `hardware.memory` | string | No | System memory (e.g., "32Gi") |
| `hardware.storage` | string | No | Storage needed (e.g., "10Gi RWX") |
| `hardware.multi_node` | boolean | No* | Multi-node setup required |

*Required if `hardware` section is present.

### Time Estimates

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `duration_estimate.setup` | string | No | Setup time (e.g., "15 minutes") |
| `duration_estimate.execution` | string | No* | Execution time (e.g., "2 hours") |
| `duration_estimate.total` | string | No* | Total time |

*Required if `duration_estimate` section is present.

### Classification

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tags` | list[string] | No | Tags from predefined list |
| `use_case` | string | No | Use case from predefined list |
| `complexity` | enum | No | `beginner`, `intermediate`, or `advanced` |

### Components

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `components.rhoai` | list[string] | Yes | RHOAI components from predefined list |
| `components.external` | list[string] | No | External services (e.g., huggingface-hub) |

---

## Predefined Vocabularies

### Tags

- `fine-tuning` - Model fine-tuning techniques
- `knowledge-tuning` - Knowledge injection methods
- `compression` - Model compression
- `quantization` - Model quantization
- `RAG` - Retrieval-augmented generation
- `evaluation` - Model evaluation
- `distributed-training` - Multi-GPU or multi-node training
- `pipeline` - Workflow pipelines
- `inference` - Model inference/serving
- `continual-learning` - Continual/lifelong learning

### Use Cases

- `model-compression` - Reducing model size/requirements
- `model-fine-tuning` - Fine-tuning pretrained models
- `knowledge-injection` - Adding domain knowledge
- `continual-learning` - Learning without forgetting
- `domain-customization` - Customizing for specific domains
- `model-evaluation` - Evaluating model performance
- `data-generation` - Generating synthetic training data

### RHOAI Components

- `workbench` - RHOAI Workbench/JupyterLab
- `data-science-pipelines` - Kubeflow Pipelines
- `training-operator` - Kubeflow Training Operator
- `model-serving` - Model serving infrastructure
- `kserve` - KServe model serving

---

## Validation

All metadata files are automatically validated by CI using `tests/validation/test_example_metadata.py`. To validate locally:

```bash
pytest tests/validation/test_example_metadata.py -v
```
