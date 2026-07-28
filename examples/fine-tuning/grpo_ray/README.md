# GRPO Fine-Tuning on Ray with Training Hub

This example demonstrates how to run Training Hub's [GRPO (Group Relative Policy Optimization)](https://github.com/Red-Hat-AI-Innovation-Team/training_hub?tab=readme-ov-file#grpo) on Ray using CodeFlare SDK and KubeRay on Red Hat OpenShift AI.

## What is GRPO?

GRPO is a reinforcement learning from verifiable rewards (RLVR) algorithm that improves a model's outputs by comparing groups of responses and reinforcing the better ones:

- Generates multiple candidate responses per prompt
- Scores them with a reward function (e.g. tool-call correctness)
- Uses the group's relative ranking to compute advantage signals
- Updates LoRA adapter weights via policy gradient with group normalization

Each training iteration has two phases:

1. **Rollout phase** — vLLM generates candidate responses and a reward function scores them
2. **Train phase** — The policy network updates LoRA adapter weights using the advantage signals

The verl backend orchestrates this using Ray-native actors with FSDP for the policy network and vLLM for inference, distributing across multiple GPUs.

### Training Task: Tool-Call Verification

The example uses the [Agent-Ark/Toucan-1.5M](https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M) dataset, which contains tool-calling conversations. The reward function verifies that the model produces syntactically correct tool calls with the expected function name and arguments.

## RHOAI Compatibility

This example is compatible with RHOAI version 3.5.

> [!NOTE]
> The Ray runtime image used in this example is **Tested & Verified** but not yet officially supported.

## Requirements

- An OpenShift cluster with OpenShift AI (RHOAI 3.5) installed:
  - The `dashboard`, `workbenches`, and `ray` components enabled
- Worker node(s) with NVIDIA GPUs (Ampere-based or newer, 80GB VRAM recommended per GPU)
- `codeflare-sdk` installed in the workbench (pre-installed in RHOAI workbench images)

## Hardware Requirements

### Workbench Requirements

The workbench only submits and monitors the RayJob — no GPU is needed on the workbench itself unless you want to test the trained model afterward.

| Use Case | GPU | CPU | Memory |
|----------|-----|-----|--------|
| Job submission and monitoring | None | 2 cores | 8Gi |
| Job submission + model evaluation after training | 1× GPU (40GB+ VRAM) | 8 cores | 64Gi |

### Ray Cluster Requirements

verl distributes training across multiple nodes using Ray-native actors with FSDP for the policy network and vLLM for inference generation.

The default configuration uses 1 head node (coordination only, no GPUs) + 1 worker node with 4 GPUs (4 GPUs total).

| Component | GPU | GPU Type | CPU | Memory |
|-----------|-----|----------|-----|--------|
| Head pod | None | — | 4 cores | 32Gi |
| Worker pod (×1) | 4× GPU | NVIDIA A100-80GB or H100 | 8 cores | 192Gi request / 256Gi limit |

> [!NOTE]
>
> - Memory requirements scale with model size and number of GPUs. The above values suit the example configuration (Qwen3-4B with LoRA, FSDP across 4× A100-80GB, vLLM with `gpu_memory_utilization=0.20`).
> - Scale by adding more worker pods or increasing GPUs per node.

## GRPO-specific Considerations

- **`gpu_memory_utilization`**: Controls how much GPU memory vLLM reserves for inference. The default `0.20` leaves the majority for FSDP training. Adjust based on model size and available VRAM.
- **HuggingFace token**: Not strictly required for public models (e.g. Qwen3-4B) but recommended to avoid rate limits. Pass as `HF_TOKEN` environment variable.

## Setup

### Prerequisites

1. Log in to your OpenShift cluster (`oc login`)
2. Ensure the KubeRay operator is running in your cluster
3. Verify GPU nodes are available: `oc get nodes -l nvidia.com/gpu.present=true`

### Running the Example

From a RHOAI workbench:

1. Clone this repository and navigate to `examples/fine-tuning/grpo_ray/`:

   ```bash
   git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
   ```

2. Open [`grpo_lora-rayjob.ipynb`](./grpo_lora-rayjob.ipynb)
3. Follow the notebook instructions — update the namespace, image, and authentication details for your cluster

> [!NOTE]
> You will need a Hugging Face token if using gated models.
> Set the `HF_TOKEN` variable in the configuration section.
> You can skip the token for non-gated models like Qwen3-4B.
