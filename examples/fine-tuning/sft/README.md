# SFT Fine-Tuning with Training Hub

This example provides an overview of the [SFT algorithm from Training Hub](https://github.com/Red-Hat-AI-Innovation-Team/training_hub?tab=readme-ov-file#supervised-fine-tuning-sft) and demonstrates how to use it with Red Hat OpenShift AI.

## What is SFT?

Supervised Fine-Tuning (SFT) is the standard approach for adapting a pre-trained language model to follow instructions or perform specific tasks. During SFT the model learns from labeled examples of input-output pairs:

- Updates **all model weights** using instruction/response training data
- Directly optimizes the model to produce desired outputs for given inputs
- Supports multi-turn conversation formats with system, user, and assistant roles

SFT is the most straightforward fine-tuning method and serves as the foundation that other techniques (LoRA, OSFT) build upon or optimize around.

## Execution modes

SFT supports two execution modes:

- **Interactive Notebooks (Single Node Fine Tuning)**: training runs directly in a workbench on a single pod, demonstrated by `sft-interactive-notebook.ipynb`.
- **Training Jobs (Distributed Fine Tuning with Kubeflow Trainer)**: training runs as distributed jobs across multiple nodes/pods via Kubeflow Trainer, demonstrated by `sft-distributed.ipynb`.

While workbench setup is similar for both, we highlight specific configuration differences below.

To learn more about these execution modes, see the [fine-tuning execution modes overview](../README.md#execution-modes).

## RHOAI compatibility

This example is compatible with RHOAI version 3.4. For a version compatible with RHOAI 3.3 see [this README](../rhoai-3.3/training-hub/sft/README.md).

> [!IMPORTANT]
> This example has been tested with the configurations listed in the hardware requirements below.
> If you have a different hardware configuration you can check [training-hub memory estimator](https://github.com/Red-Hat-AI-Innovation-Team/training_hub/tree/main/examples#memory-estimation-experimental--in-development) to validate your
> hardware configuration will be sufficient to run this example.

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
>   - For the interactive example an accelerator is required for the workbench to execute the fine tuning with SFT.

### Running the example notebooks

- From the workbench, clone this repository: `https://github.com/red-hat-data-services/red-hat-ai-examples.git`
- Navigate to the `examples/fine-tuning/sft` directory and open the [`sft-interactive-notebook.ipynb`](./sft-interactive-notebook.ipynb) notebook or [`sft-distributed.ipynb`](./sft-distributed.ipynb) as required.

> [!NOTE]
>
> - You will need a Hugging Face token if using gated models (e.g., Llama models).
>   Set the `HF_TOKEN` environment variable in your job configuration.
>   You can skip the token if switching to non-gated models.

You can now proceed with the instructions from the notebook. Enjoy!
