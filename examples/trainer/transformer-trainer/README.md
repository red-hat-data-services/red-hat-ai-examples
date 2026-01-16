# Distributed Training with TransformersTrainer on Red Hat OpenShift AI

This example demonstrates how to use the `TransformersTrainer` from the Kubeflow SDK to run distributed fine-tuning of HuggingFace models on Red Hat OpenShift AI.

## Overview

`TransformersTrainer` is a specialized trainer that extends the Kubeflow `CustomTrainer` with:

- **Automatic progress tracking** — Real-time visibility into training steps, epochs, loss, and ETA
- **JIT checkpointing** — Automatic checkpoint saves when pods are terminated (preemption, scaling, maintenance)
- **Simplified distributed training** — No manual configuration of PyTorch distributed settings

This example fine-tunes a DistilBERT model on the IMDB sentiment classification dataset using distributed training across multiple GPUs.

## Requirements

### OpenShift AI cluster

- Red Hat OpenShift AI (RHOAI) 3.2+ with:
  - `trainingoperator` component enabled
  - `workbenches` component enabled

### Hardware requirements

#### Training job

| Component | Configuration | Notes |
|-----------|---------------|-------|
| Training pods | 2 nodes x 1 GPU | Configurable in notebook |
| GPU type | NVIDIA A100/L40/T4 or equivalent | Any CUDA-compatible GPU |
| Memory | 16Gi per pod | Adjust based on model size |

#### Workbench

| Image | GPU | CPU | Memory | Notes |
|-------|-----|-----|--------|-------|
| Minimal Python 3.12 | Optional | 2 cores | 8Gi | GPU recommended for faster testing |

#### Storage

| Purpose | Size | Access Mode | Notes |
|---------|------|-------------|-------|
| Checkpoints (PVC) | 5Gi | ReadWriteMany (RWX) | Required for JIT checkpointing |

## Setup

### 1. Create a workbench

1. Access the OpenShift AI dashboard
2. Navigate to **Data Science Projects** and create or select a project
3. Click **Create a workbench** with the following settings:
   - **Image**: `Jupyter | Minimal | Python 3.12`
   - **Container size**: Medium
   - **Accelerator**: Optional (for model evaluation)

### 2. Create shared storage (optional, for checkpointing)

If you want to use JIT checkpointing:

1. In your project, go to **Storage**
2. Click **Create storage**
3. Configure:
   - **Name**: `training-checkpoints`
   - **Storage class**: Select one with RWX support (NFS, CephFS, etc.)
   - **Access mode**: ReadWriteMany
   - **Size**: 5Gi

### 3. Clone the repository

From your workbench, clone this repository:

```bash
git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
```

Navigate to `examples/trainer/transformer-trainer` and open the notebook.

## Running the example

The notebook walks you through:

1. **Installing dependencies** — Kubeflow SDK and required packages
2. **Defining the training function** — HuggingFace Trainer setup for IMDB classification
3. **Configuring TransformersTrainer** — Distributed training settings
4. **Submitting the job** — Using the Kubeflow SDK
5. **Monitoring progress** — Real-time training metrics
6. **Cleanup** — Deleting the training job

## Key features demonstrated

### Progress tracking

The notebook shows how to view real-time training progress:

- Via the OpenShift AI dashboard
- Via CLI using `oc get trainjob` commands
- Training metrics: loss, learning rate, steps, epochs, ETA

### JIT checkpointing (optional)

The notebook includes an optional section demonstrating:

- Configuring PVC storage for checkpoints
- Using the `pvc://` URI scheme
- Suspending and resuming training jobs

## Customization

You can modify the example for your use case:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_nodes` | 2 | Number of training nodes |
| `resources_per_node` | 1 GPU | GPUs per node |
| Model | `distilbert-base-uncased` | Any HuggingFace model |
| Dataset | `imdb` | Any HuggingFace dataset |
| `num_train_epochs` | 1 | Training epochs |

## Troubleshooting

### Job not starting

```bash
# Check TrainJob status
oc get trainjob <job-name> -o yaml

# Check for pending pods
oc get pods -l trainer.kubeflow.org/train-job-name=<job-name>
```

### Progress tracking not working

Verify the logs show initialization:

```bash
oc logs <pod-name> -c node | grep -i "progression"
```

Expected output:
```
[Kubeflow] Initializing progression tracking
[Kubeflow] Progression tracking enabled
```

## Additional resources

- [RHAI trainers guide](https://access.redhat.com/articles/7136179) — Detailed progress tracking and checkpointing documentation
- [Kubeflow SDK repository](https://github.com/opendatahub-io/kubeflow-sdk) — SDK source and API reference
- [Troubleshooting guide](https://access.redhat.com/articles/7136148) — Common issues and solutions
