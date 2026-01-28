# Real-Time Progress Tracking with TransformersTrainer

This example demonstrates how to monitor distributed training progress in real-time using `TransformersTrainer` from Kubeflow Trainer v2 on Red Hat OpenShift AI.

## Overview

In this example, we fine-tune the **Qwen 2.5 1.5B Instruct** model on the **Stanford Alpaca** instruction-following dataset. The training runs on 2 GPU nodes with automatic progress tracking enabled, allowing you to monitor training metrics in real-time from the OpenShift AI Dashboard.

### Key Features

| Feature | Description |
| --- | --- |
| **Automatic Progress Tracking** | TransformersTrainer auto-injects a `KubeflowProgressCallback` that exposes training metrics via HTTP |
| **Real-Time Metrics** | View current step, epoch, loss, and estimated time remaining in the OpenShift AI Dashboard |
| **PVC-Based Checkpointing** | Save model checkpoints to a shared PersistentVolumeClaim for durability and resume capability |
| **Distributed Training** | Run training across multiple GPU nodes using PyTorch's DistributedDataParallel (DDP) |

> [!IMPORTANT]
> This example has been tested with OpenShift AI 3.2 and Kubeflow Trainer v2.
> If you have different hardware configuration, adjust the `resources_per_node` settings accordingly.

## Requirements

* An OpenShift cluster with OpenShift AI (RHOAI) 3.2 installed:
  * The `dashboard`, `trainer` and `workbenches` components enabled
* At least 2 worker nodes with NVIDIA GPUs
* A dynamic storage provisioner supporting RWX PVC provisioning

## Setup

### Setup Workbench

* Access the OpenShift AI dashboard, for example from the top navigation bar menu:
![](./images/entry_page.png)

* Log in, then go to _Data Science Projects_ and create a project:
![](./images/project_page.png)

* Once the project is created, click on _Create a workbench_:
![](./images/create_workbench.png)

* Then create a workbench with the following settings:
  * Select a hardware profile for your workbench:
    ![](./images/create_workbench_select_hardawre_profile.png)
  * Choose the appropriate hardware profile based on your needs:
    ![](./images/create_workbench_hardware_profile_options.png)
    > [!NOTE]
    > Adding an accelerator is only needed to test the fine-tuned model from within the workbench.
  * Create a storage that'll be shared between the workbench and the fine-tuning runs.
    Make sure it uses a storage class with RWX capability and name it `shared`:
    ![](./images/create_storage.png)
    ![](./images/create_storage_2.png)
  * Configure the storage with ReadWriteMany (RWX) access mode:
    ![](./images/create_RWX_storage.png)
    > [!NOTE]
    > The shared PVC will be mounted at `/opt/app-root/src/shared` in the workbench.

* From "Workbenches" page, click on _Open_ when the workbench you've just created becomes ready:
![](./images/start_workbench.png)

* From the workbench, clone this repository:

  ```bash
  git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
  ```

* Navigate to `red-hat-ai-examples/examples/trainer/progress-tracking/` and open the `progress-tracking-example.ipynb` notebook

## Environment Variables

Before running the notebook, ensure you have the following environment variables set:

| Variable | Description |
| --- | --- |
| `OPENSHIFT_API_URL` | Your OpenShift API server URL (auto-set in workbench) |
| `NOTEBOOK_USER_TOKEN` | Authentication token for API access (auto-set in workbench) |

## How Progress Tracking Works

When you use `TransformersTrainer` with `enable_progression_tracking=True` (the default):

1. **Automatic Instrumentation:** TransformersTrainer injects a `KubeflowProgressCallback` into your HuggingFace `Trainer`
2. **HTTP Metrics Server:** A lightweight HTTP server starts on port 28080, exposing metrics as JSON
3. **Dashboard Integration:** OpenShift AI Dashboard polls these metrics and displays real-time progress

### Available Metrics

| Metric | Description |
| --- | --- |
| `progressPercentage` | Overall completion percentage (0-100) |
| `currentStep` / `totalSteps` | Training step progress |
| `currentEpoch` / `totalEpochs` | Epoch progress |
| `estimatedRemainingSeconds` | Estimated time to completion |
| `trainMetrics.loss` | Current training loss value |
| `trainMetrics.learning_rate` | Current learning rate |

### Viewing Progress in the Dashboard

Once your training job is running, you can monitor its progress directly from the OpenShift AI Dashboard:

1. Navigate to **Training Jobs** in the left sidebar to see your running jobs:
![](./images/training_progress.png)

2. Click on a job to view detailed resource allocation and pod status:
![](./images/trainjob_resources.png)

3. You can **pause** (suspend) a running job to free up resources. When paused, JIT checkpointing will save the current state:
![](./images/pause_job.png)

> [!TIP]
> The dashboard automatically refreshes progress metrics every 30 seconds (configurable via `metrics_poll_interval_seconds`).

## Model and Dataset

### Model: Qwen 2.5 1.5B Instruct

A compact instruction-tuned language model from the Qwen family:

* **Parameters:** 1.5 billion
* **Context Length:** 32K tokens
* **Languages:** Multilingual with strong English and Chinese support
* **Use Case:** Ideal for instruction-following, chat, and text generation tasks

### Dataset: Stanford Alpaca

A widely-used instruction-following dataset:

* **Source:** Stanford University
* **Size:** 52,000 instruction-response pairs (we use 500 samples for this demo)
* **Format:** Instruction, optional input, and response

Sample format:

```text
### Instruction:
Give three tips for staying healthy.

### Response:
1. Eat a balanced diet...
2. Exercise regularly...
3. Get enough sleep...
```

## Validation

This example has been validated with the following configuration:

### Qwen 2.5 1.5B Instruct - Alpaca Dataset - 2x NVIDIA A100/80GB

* **Infrastructure:**
  * OpenShift AI 3.2
  * 2x NVIDIA-A100-SXM4-80GB

* **Training Configuration:**

  ```yaml
  num_train_epochs: 1
  per_device_train_batch_size: 2
  gradient_accumulation_steps: 4
  learning_rate: 2e-5
  bf16: true
  save_steps: 20
  ```

* **Job Configuration:**

  ```yaml
  num_nodes: 2
  resources_per_node:
    nvidia.com/gpu: 1
    memory: 16Gi
    cpu: 4
  enable_progression_tracking: true
  metrics_poll_interval_seconds: 30
  ```

* **Training Time:** ~1 minute for 500 samples

## TransformersTrainer Quick Reference

| Parameter | Description | Default |
| --- | --- | --- |
| `func` | Training function using `transformers.Trainer` | Required |
| `num_nodes` | Number of distributed training nodes | Required |
| `resources_per_node` | GPU, CPU, memory per node | Required |
| `enable_progression_tracking` | Enable real-time metrics server | `True` |
| `enable_jit_checkpoint` | Enable JIT checkpointing on preemption | `False` |
| `metrics_poll_interval_seconds` | How often controller polls metrics | `30` |

## Next Steps

* **Scale Up:** Increase `num_nodes` for larger models or datasets
* **Use LoRA:** Add PEFT/LoRA for memory-efficient fine-tuning
* **Try Other Models:** This pattern works with any HuggingFace model
* **Enable JIT Checkpointing:** Use `enable_jit_checkpoint=True` for automatic checkpoint saving on preemption

## Resources

* [Kubeflow Trainer Documentation](https://www.kubeflow.org/docs/components/trainer/)
* [HuggingFace Transformers](https://huggingface.co/docs/transformers/)
* [Stanford Alpaca Dataset](https://huggingface.co/datasets/tatsu-lab/alpaca)
* [Qwen 2.5 Model](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
