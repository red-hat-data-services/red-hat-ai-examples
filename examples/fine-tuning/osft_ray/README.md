# OSFT Continual Learning on Ray with Training Hub

This example demonstrates how to run Training Hub's [OSFT (Orthogonal Subspace Fine-Tuning)](https://github.com/Red-Hat-AI-Innovation-Team/training_hub?tab=readme-ov-file#orthogonal-subspace-fine-tuning-osft) on Ray using CodeFlare SDK and KubeRay on Red Hat OpenShift AI.

## What is OSFT?

Orthogonal Subspace Fine-Tuning (OSFT) is a continual learning technique based on [Nayak et al. (2025)](https://arxiv.org/abs/2504.07097) that allows fine-tuning without catastrophic forgetting:

- Enables continual learning without losing previously learned capabilities
- No supplementary dataset needed to maintain original model distribution
- Significantly reduces data requirements for customizing instruction-tuned models
- Memory requirements similar to standard SFT

### Data Format

OSFT supports two data formats:

**Standard messages format (recommended):**

```json
{"messages": [{"role": "user", "content": "Hello!"}, {"role": "assistant", "content": "Hi there!"}]}
```

**Pre-processed format:**

```json
{"input_ids": [1, 2, 3, ...], "labels": [1, 2, 3, ...]}
```

## How It Works on Ray

The notebook submits a `RayJob` via CodeFlare SDK. The SDK creates a short-lived RayCluster, runs the Training Hub `osft()` entrypoint on the head node, and tears everything down on completion.

This is a **single GPU** execution — all training happens on the head pod.

> [!NOTE]
> For multi-node distributed OSFT via Kubeflow Trainer, see the [OSFT distributed example](../osft/osft-distributed.ipynb).

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

OSFT on Ray runs as a single GPU job on the head pod. The head pod needs enough GPU memory to hold the model and training state.

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
- Navigate to the `examples/fine-tuning/osft_ray` directory and open [`osft-ray.ipynb`](./osft-ray.ipynb).

> [!NOTE]
> You will need a Hugging Face token if using gated models (e.g., Llama models).
> Set the `HF_TOKEN` environment variable in your job configuration.
> You can skip the token if switching to non-gated models like Qwen2.5-1.5B-Instruct.
