# Distributed Training with TransformersTrainer on Red Hat OpenShift AI

This example demonstrates how to use the `TransformersTrainer` from the Kubeflow SDK to run distributed fine-tuning of HuggingFace models on Red Hat OpenShift AI.

## Overview

`TransformersTrainer` is a specialized trainer that extends the Kubeflow `CustomTrainer` with:

* **Automatic progress tracking** — Real-time visibility into training steps, epochs, loss, and ETA
* **Simplified distributed training** — No manual configuration of PyTorch distributed settings
* **Checkpointing (optional)** — Persist checkpoints to shared storage (PVC) using `output_dir="pvc://..."`

This example fine-tunes a DistilBERT model on the IMDB sentiment classification dataset using distributed training across multiple GPUs.

## Requirements

### OpenShift AI cluster

* Red Hat OpenShift AI (RHOAI) 3.2+ with:
  * `trainer` component enabled
  * `workbenches` component enabled

### Hardware requirements

#### Training job

| Component | Configuration | Notes |
| --- | --- | --- |
| Training pods | 2 nodes x 1 GPU | Configurable in notebook |
| GPU type | NVIDIA A100/L40/T4 or equivalent | Any CUDA-compatible GPU |
| Memory | 16Gi per pod | Adjust based on model size |

#### Workbench

| Image | GPU | CPU | Memory | Notes |
| --- | --- | --- | --- | --- |
| Minimal Python 3.12 | Optional | 2 cores | 8Gi | GPU recommended for faster testing |

#### Storage

| Purpose | Size | Access mode | Notes |
| --- | --- | --- | --- |
| Shared PVC | 5Gi+ | ReadWriteMany (RWX) | Required for multi-node training and persisting model/data/checkpoints |

## Environment variables

The notebook uses these environment variables for API authentication:

* `OPENSHIFT_API_URL` — your OpenShift API URL
* `NOTEBOOK_USER_TOKEN` — a token for API access

These are often auto-set in OpenShift AI workbenches.

## PVC mount paths (workbench vs training pods)

The notebook uses two different mount conventions:

* **Workbench mount (user-configured)**: when you attach a PVC named (for example) `shared` to the workbench, it is typically mounted at `/opt/app-root/src/<pvc-name>` (e.g. `/opt/app-root/src/shared`).
* **Training pod mount (SDK, fixed)**: when you use `TransformersTrainer(output_dir="pvc://<pvc-name>/<path>")`, the SDK mounts that PVC at `/mnt/kubeflow-checkpoints` inside the training pods.

## Setup

### 1. Access OpenShift AI Dashboard

Access the OpenShift AI dashboard from the top navigation bar menu:

![](./images/entry_page.png)

### 2. Create a Data Science Project

Log in, then go to **Data Science Projects** and create a project:

![](./images/project_page.png)

### 3. Create a Workbench

Once the project is created, click on **Create a workbench**:

![](./images/create_workbench.png)

Configure the workbench with the following settings:

* Select a hardware profile for your workbench:

![](./images/create_workbench_select_hardawre_profile.png)

* Choose the appropriate hardware profile based on your needs:

![](./images/create_workbench_hardware_profile_options.png)

> [!NOTE]
> Adding an accelerator is optional - only needed to test fine-tuned models from within the workbench.

### 4. Create Shared Storage (Required)

Create a storage with RWX access (for example, a PVC named `shared`):

![](./images/create_storage.png)

Configure the storage details:

![](./images/create_storage_2.png)

Select ReadWriteMany (RWX) access mode:

![](./images/create_RWX_storage.png)

### 5. Start the Workbench

From the "Workbenches" page, click on **Open** when your workbench is ready:

![](./images/start_workbench.png)

### 6. Clone the Repository

From your workbench, clone this repository:

```bash
git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
```

Navigate to `examples/trainer/transformer-trainer` and open the notebook.

## Running the example

The notebook walks you through:

1. **Installing dependencies** — Kubeflow SDK and required packages
2. **Configuring authentication and paths** — API access + PVC mount paths
3. **Staging model and dataset to the PVC** — Download DistilBERT + an IMDB subset from the workbench
4. **Defining the training function** — A `transformers.Trainer` training loop that loads inputs from the PVC
5. **Configuring and submitting TransformersTrainer** — Distributed training + `output_dir="pvc://..."` for persisted checkpoints
6. **Monitoring progress** — View progress in the OpenShift AI Dashboard (**Training Jobs**)
7. **Cleanup** — Deleting the training job

## Key Features Demonstrated

### Progress Tracking

Navigate to **Training Jobs** in the OpenShift AI Dashboard to view real-time training progress:

![](./images/training_progress.png)

Click on a job to view detailed resource allocation and pod status:

![](./images/trainjob_resources.png)

### Checkpointing (optional)

You can **pause** (suspend) a running job to free up resources. When paused, JIT checkpointing saves the current state:

![](./images/pause_job.png)

The notebook demonstrates:

* Configuring PVC storage for checkpoints
* Using the `pvc://` URI scheme
* Suspending and resuming training jobs

## Customization

You can modify the example for your use case:

| Parameter | Default | Description |
| --- | --- | --- |
| `num_nodes` | 2 | Number of training nodes |
| `resources_per_node` | 1 GPU | GPUs per node |
| Model | `distilbert-base-uncased` | Any HuggingFace model |
| Dataset | `stanfordnlp/imdb` | Any HuggingFace dataset repo |
| `num_train_epochs` | 1 | Training epochs |
| PVC | `shared` | Update `PVC_NAME` in the notebook if you use a different PVC name |

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

```text
[Kubeflow] Initializing progression tracking
[Kubeflow] Progression tracking enabled
```

### Dataset download fails with 404

If you see an error similar to `HfHubHTTPError: 404 Client Error ... /api/datasets/imdb/revision/...`, use the canonical dataset repo ID in the notebook:

* `DATASET_NAME="stanfordnlp/imdb"`
* `DATASET_REVISION="main"`
