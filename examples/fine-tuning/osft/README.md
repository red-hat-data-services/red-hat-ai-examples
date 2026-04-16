# OSFT Continual Learning on Red Hat OpenShift AI

This example provides an overview of the [OSFT algorithm from Training Hub](https://github.com/Red-Hat-AI-Innovation-Team/training_hub/tree/main?tab=readme-ov-file#orthogonal-subspace-fine-tuning-osft) and demonstrates how to use it with Red Hat OpenShift AI.

## Overview

Fine-tuning language models is hard—you need good data, lots of resources, and even small changes can cause problems. This makes it tough to add new abilities to a model. This problem is called continual learning and is what our new training technique, orthogonal subspace fine-tuning (OSFT), solves.

The OSFT algorithm implements Orthogonal Subspace Fine-Tuning based on Nayak et al. (2025), arXiv:2504.07097. This algorithm allows for continual training of pre-trained or instruction-tuned models without the need of a supplementary dataset to maintain the distribution of the original model/dataset that was trained.

**Key Benefits:**

- Enables continual learning without catastrophic forgetting
- No need for supplementary datasets to maintain original model distribution
- Significantly reduces data requirements for customizing instruction-tuned models
- Memory requirements similar to standard SFT

### Data Format Requirements

Training Hub's OSFT algorithm supports both **processed** and **unprocessed** data formats via the [mini-trainer](https://github.com/Red-Hat-AI-Innovation-Team/mini_trainer/) backend.

#### Option 1: Standard Messages Format (Recommended)

Your training data should be a **JSON Lines (.jsonl)** file containing messages data:

```json
{"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello!"}, {"role": "assistant", "content": "Hi there! How can I help you?"}]}
{"messages": [{"role": "user", "content": "What is OSFT?"}, {"role": "assistant", "content": "OSFT stands for Orthogonal Subspace Fine-Tuning..."}]}
```

#### Message Structure

- **`role`**: One of `"system"`, `"user"`, `"assistant"`, or `"pretraining"`
- **`content`**: The text content of the message
- **`reasoning_content`** (optional): Additional reasoning traces

#### Masking Control with `unmask_messages` Parameter

Control training behavior during data processing:

**Standard instruction tuning (default):**

```python
osft(..., unmask_messages=False)  # Only assistant responses used for loss
```

**Pretraining mode:**

```python
osft(..., unmask_messages=True)   # All content except system messages used for loss
```

#### Option 2: Pre-processed Dataset

If you have pre-processed data with `input_ids` and `labels` fields:

```json
{"input_ids": [1, 2, 3, ...], "labels": [1, 2, 3, ...]}
{"input_ids": [4, 5, 6, ...], "labels": [4, 5, 6, ...]}
```

Use with:

```python
osft(..., use_processed_dataset=True)
```

## Execution modes

OSFT supports two execution modes:

- **Interactive Notebooks (Single Node Fine Tuning)**: training runs directly in a workbench on a single pod, demonstrated by `osft-interactive-notebook.ipynb`.
- **Training Jobs (Distributed Fine Tuning with Kubeflow Trainer)**: training runs as distributed jobs across multiple nodes/pods via Kubeflow Trainer, demonstrated by `osft-distributed.ipynb`.

While workbench setup is similar for both, we highlight specific configuration differences below.

To learn more about these execution modes, see the [fine-tuning execution modes overview](../README.md#execution-modes).

## RHOAI compatibility

This example is compatible with RHOAI version 3.4. For a version compatible with RHOAI 3.3 see [this README](../rhoai-3.3/osft/README.md).

## Requirements

- An OpenShift cluster with OpenShift AI (RHOAI 3.4) installed:
  - The `dashboard` and `workbenches` components enabled
  - The `trainer` component should be enabled if running the distributed notebook.
- Sufficient worker nodes with NVIDIA GPUs (Ampere-based or newer recommended).
- (Distributed only) A dynamic storage provisioner supporting RWX PVC provisioning. Talk to your cluster administrator about RWX storage options.

## Hardware requirements

For the workbench image, the example was run on `Training Jupyter Pytorch CUDA Python` and `Training Jupyter Pytorch CPU Python`.
This is a single image serving both as training runtime and jupyter notebook and comes with pre-installed dependencies required
to seamlessly run fine-tuning jobs.

### Workbench Requirements (Interactive example)

| Image Type | Use Case | GPU | CPU | Memory | Notes |
|------------|----------|-----|-----|--------|-------|
| Training Jupyter Pytorch CUDA Python | NVIDIA GPU training | 1× GPU | 4 cores | 32Gi | Recommended for faster training |

> [!NOTE]
>
> - **Interactive notebooks (single node fine tuning)** are recommended for smaller training jobs.
> - For larger training jobs, consider the **training jobs (distributed fine tuning with Kubeflow Trainer)** approach.

### Training Job Requirements (Distributed example)

| Component | Configuration | GPU per node | Total GPU | GPU Type (per GPU) | CPU | Memory |
|-----------|--------------|---|---|------------|-----|--------|
| Training Pods | 2 nodes × 2 GPUs | 2 | 4 | NVIDIA L40/L40S or equivalent | 4 cores/pod | 32Gi/pod |

> [!NOTE]
>
> - This example was tested on 2 nodes × 2 GPUs provided by L40S however, it will work on smaller/larger configurations.
> - Flash Attention is required for efficient training with OSFT.
> - CPU and Memory requirements scale with batch size and model size. Above suit the example as it is.
> - Worker pods are configurable from the `client.create_job` call within the notebook.

### Workbench Requirements (Distributed example)

| Image Type | Use Case | GPU | CPU | Memory | Notes |
|------------|----------|-----|-----|--------|-------|
| Training Jupyter Pytorch CPU Python | CPU-based evaluation | None | 6 cores | 24Gi | Slower evaluation |
| Training Jupyter Pytorch CUDA Python | NVIDIA GPU evaluation (Example Default) | 1× GPU | 2 cores | 8Gi | Recommended for faster testing |

> [!NOTE]
>
> - Workbench GPU is optional for distributed mode but recommended for faster model evaluation and required for interactive mode.
> - Evaluation was performed on L40S GPU however, it will work on smaller/larger configurations.
> - Workbench resources and accelerator are configurable in `Create Workbench` view on RHOAI Platform.

### Storage Requirements (Distributed example)

| Purpose | Size | Access Mode | Storage Class | Notes |
|---------|------|-------------|---------------|-------|
| Shared Storage (PVC) total | 50Gi (Example Default) | RWX | Dynamic provisioner required | Shared between workbench and training pods |

> [!NOTE]
>
> - Storage can be created in `Create Workbench` view on RHOAI Platform, however, dynamic RWX provisioner is required to be configured prior to creating shared file storage in RHOAI.
> - Shared storage is not required for the interactive example as dataset, model download and training all happen on the same pod.

## Setup

### Setup Workbench

**Step 1.** Access the OpenShift AI dashboard, for example from the top navigation bar menu:

![](../images/01.png)

**Step 2.** Log in, then go to **_Data Science Projects_** and create a project:

![](../images/02.png)

**Step 3.** Once the project is created, click on **_Create a workbench_**:

![](../images/03.png)

**Step 4.** Select the appropriate Workbench image based on interactive or distributed use case. See options above:

![](../images/04a.png)

**Step 5.** You may want to add a **Hardware Profile** for reuse within the Workbench settings:

![](../images/04b.png)

**Step 6.** Select the Hardware profile just created:

![](../images/04c.png)

> [!NOTE]
> Adding an accelerator (GPU) for the distributed use case is only needed to test the fine-tuned model from within the workbench so you can spare an accelerator if you plan to skip that step. An accelerator (GPU) is required in interactive mode as the training happens on the workbench pod.

**Step 7.** For distributed training, create **shared storage** that'll be shared between the workbench and the training pods. Make sure it uses a storage class with RWX capability:

![](../images/04d.png)

> [!NOTE]
> For the interactive example, dataset, model download, and training all happen on the same pod, so shared storage is not required.
> You can attach an existing shared storage if you already have one instead.

**Step 8.** Review the storage configuration and click "Create workbench":

![](../images/04e.png)

**Step 9.** From "Workbenches" page, click on **_Open_** when the workbench you've just created becomes ready:

![](../images/05.png)

> [!IMPORTANT]
>
> - By default:
>   - The distributed example goes through training on two nodes (2×L40/L40S) with two GPUs each (2×48GB). However, it can be tweaked to run on smaller configurations.
>   - If you want to do model evaluation as part of the distributed example, ideally an accelerator is attached to the workbench.
>   - For the interactive example an accelerator is required for the workbench to execute the fine tuning with OSFT.

### Running the example notebooks

- From the workbench, clone this repository: `https://github.com/red-hat-data-services/red-hat-ai-examples.git`
- Navigate to the `examples/fine-tuning/osft` directory and open the [`osft-interactive-notebook.ipynb`](./osft-interactive-notebook.ipynb) notebook or [`osft-distributed.ipynb`](./osft-distributed.ipynb) as required.

> [!NOTE]
>
> - You will need a Hugging Face token if using gated models (e.g., Llama models).
>   Set the `HF_TOKEN` environment variable in your job configuration.
>   You can skip the token if switching to non-gated models.

You can now proceed with the instructions from the notebook. Enjoy!
