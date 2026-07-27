# SFT Fine-Tuning on Ray with Training Hub

This example demonstrates how to run Training Hub's [SFT (Supervised Fine-Tuning)](https://github.com/Red-Hat-AI-Innovation-Team/training_hub?tab=readme-ov-file#supervised-fine-tuning-sft) on Ray using CodeFlare SDK and KubeRay on Red Hat OpenShift AI.

## What is SFT?

Supervised Fine-Tuning (SFT) is the standard approach for adapting a pre-trained language model to follow instructions or perform specific tasks:

- Updates **all model weights** using instruction/response training data
- Directly optimizes the model to produce desired outputs for given inputs
- Supports multi-turn conversation formats with system, user, and assistant roles

SFT is the most straightforward fine-tuning method and serves as the foundation that other techniques (LoRA, OSFT) build upon or optimize around.

### Training Task: Structured JSON Output

The example trains [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) to reliably produce structured JSON output when given tabular data — a common requirement for agentic applications. We use the [Table-GPT](https://huggingface.co/datasets/LipengCS/Table-GPT) dataset from Microsoft.

## How It Works on Ray

The notebook submits a `RayJob` via CodeFlare SDK. The SDK creates a short-lived RayCluster, runs the Training Hub `sft()` entrypoint on the head node, and tears everything down on completion.

This is a **single GPU** execution — all training happens on the head pod.

> [!NOTE]
> For multi-node distributed SFT via Kubeflow Trainer, see the [SFT distributed example](../sft/sft-distributed.ipynb).

## RHOAI Compatibility

This example is compatible with RHOAI version 3.5.

> [!NOTE]
> The Ray runtime image used in this example is **Tested & Verified** but not yet officially supported.

## Requirements

- An OpenShift cluster with OpenShift AI (RHOAI 3.5) installed:
  - The `dashboard`, `workbenches`, and `ray` components enabled
- Worker node(s) with NVIDIA GPUs (Ampere-based or newer, 48GB+ VRAM recommended per GPU)
- A PVC (RWX) provisioned with the model and training dataset accessible from Ray pods
- `codeflare-sdk` installed in the workbench (pre-installed in RHOAI workbench images)

## Hardware Requirements

### Workbench Requirements

The workbench only submits and monitors the RayJob — no GPU is needed on the workbench unless you want to evaluate the trained model afterward.

| Use Case | GPU | CPU | Memory |
|----------|-----|-----|--------|
| Job submission and monitoring | None | 2 cores | 8Gi |
| Job submission + model evaluation after training | 1× GPU (24GB+ VRAM) | 4 cores | 32Gi |

### Ray Cluster Requirements

SFT on Ray runs as a single GPU job on the head pod. The head pod needs enough GPU memory to hold the model and training state.

| Component | GPU | GPU Type | CPU | Memory |
|-----------|-----|----------|-----|--------|
| Head pod | 1× GPU | NVIDIA L40S/A100 (48GB+ VRAM) | 4 cores | 64Gi |

> [!NOTE]
>
> - Memory requirements scale with model size and sequence length. The above values suit the example configuration (Qwen2.5-1.5B-Instruct with `max_seq_len=512`).
> - Larger models may require more GPU VRAM and system memory.

### Storage Requirements

| Purpose | Size | Access Mode | Notes |
|---------|------|-------------|-------|
| PVC with model + dataset | 20Gi+ | RWX | Must be accessible from Ray pods |

## Setup

### Setup Workbench

**Step 1.** Access the OpenShift AI dashboard, for example from the top navigation bar menu:

![](../images/01.png)

**Step 2.** Log in, then go to **_Data Science Projects_** and create a project:

![](../images/02.png)

**Step 3.** Once the project is created, click on **_Create a workbench_**:

![](../images/03.png)

**Step 4.** Select a workbench image. For Ray job submission, a CPU-only workbench is sufficient — the training happens on the Ray cluster, not the workbench. Use a GPU workbench only if you want to evaluate the trained model afterward:

![](../images/04a.png)

**Step 5.** You may want to create a **Hardware Profile**. A GPU is **not required** for job submission — only for optional model evaluation after training:

![](../images/04b.png)

**Step 6.** Select the Hardware profile you want to use:

![](../images/04c.png)

> [!NOTE]
> Adding an accelerator (GPU) is only needed to test the fine-tuned model from within the workbench. You can skip the accelerator if you plan to only submit and monitor the Ray job.

**Step 7.** Create **shared storage** for the model and training data. This PVC must use a storage class with RWX capability so it can be mounted by the Ray pods:

![](../images/04d.png)

**Step 8.** Review the storage configuration and click "Create workbench":

![](../images/04e.png)

**Step 9.** From "Workbenches" page, click on **_Open_** when the workbench you've just created becomes ready:

![](../images/05.png)

### Running the Example

- From the workbench, clone this repository: `https://github.com/red-hat-data-services/red-hat-ai-examples.git`
- Navigate to the `examples/fine-tuning/sft_ray` directory and open [`sft-ray.ipynb`](./sft-ray.ipynb).

> [!NOTE]
> You will need a Hugging Face token if using gated models (e.g., Llama models).
> Set the `HF_TOKEN` environment variable in your job configuration.
> You can skip the token if switching to non-gated models like Qwen2.5-1.5B-Instruct.
