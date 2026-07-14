# Fine-tuning Examples Overview

This directory contains end-to-end examples for fine-tuning large language models on Red Hat OpenShift AI (RHOAI).

All examples are built primarily on top of **Training Hub** algorithms running on the RHOAI platform, currently:

- **SFT (Supervised Fine-Tuning)**
- **OSFT (Orthogonal Subspace Fine-Tuning)**
- **LoRA + SFT (Low-Rank Adaptation)**

For detailed algorithm documentation and configuration options, see the upstream [Training Hub documentation](https://github.com/Red-Hat-AI-Innovation-Team/training_hub/tree/main).

---

## Execution Modes

There are four ways to run fine tuning examples:

1. **Interactive (single node fine tuning)**
2. **Distributed (distributed fine tuning with Kubeflow Trainer)**
3. **Distributed on Ray (distributed fine tuning with KubeRay and CodeFlare SDK)**
4. **Pipeline mode (automated training, model evaluation, and registration with Kubeflow Pipelines)**

### Interactive (single node fine tuning)

**What it is**

Training runs directly inside a **single Workbench pod** (your notebook environment):

- **Fast iteration** for small experiments
- **Immediate feedback** during development
- **Easy debugging** – inspect variables, logs, and intermediate artifacts in real time
- **No shared storage requirement** between Workbench and training pods (everything happens in one place)

**Recommended for**

- **Prototyping and learning**
- **Quick proofs of concept**
- Fine-tuning **smaller models and datasets** where:
  - A single node’s GPU memory is sufficient
  - Longer runtimes are acceptable

**Resource considerations**

- **All training is constrained** by the Workbench pod’s resources:
  - GPU type and count
  - CPU and memory limits
- The Workbench **must reserve a GPU** for the entire duration of training.
- If you share the Workbench for multiple tasks, training can block other GPU work on that pod.

**Learn more**

- [SFT fine-tuning example](sft/README.md)
- [OSFT fine-tuning example](osft/README.md)
- [LoRA fine-tuning example](lora/README.md)

---

### Distributed (distributed fine tuning with Kubeflow Trainer)

**What it is**

Training is offloaded to **dedicated training pods** managed by **Kubeflow Trainer**:

- **Faster training via parallelism**
  - Multiple nodes or pods working together (for example, data-parallel or FSDP configurations)
- Can handle **much larger models and datasets**
- **Built-in fault tolerance and checkpointing**
- **Integration with Kueue** for:
  - Queueing and scheduling
  - Pausing or resuming jobs
- **Decoupling runtimes from experiments**
  - Platform engineers define optimized `ClusterTrainingRuntime` configurations (images, GPU layout, libraries).
  - Data scientists choose between these runtimes without rebuilding images.

**Recommended for**

- Training **foundation models** or **large fine-tunes**
- Datasets that no longer fit comfortably in a single Workbench pod
- **Production-grade** or pre-production training where:
  - Repeatability, observability, and scheduling matter
  - You need to share infrastructure with a larger team

**Resource considerations**

- **GPU(s) required** for each training node:
- **Shared storage is required** to share data across the workbench and multiple training pods
- The Workbench can remain relatively lightweight:
  - It mainly submits jobs and monitors progress, while the heavy lifting happens in training pods.
  - Optionally perform some resource intensive evaluation in the Workbench

**Learn more**

- [SFT fine-tuning example](sft/README.md)
- [OSFT fine-tuning example](osft/README.md)
- [LoRA fine-tuning example](lora/README.md)

---

### Distributed on Ray (distributed fine tuning with KubeRay)

**What it is**

Training is offloaded to a **Ray cluster** managed by **KubeRay**, submitted via **CodeFlare SDK**:

- **Multi-GPU training** using Ray-native distribution (FSDP, Ray Train `TorchTrainer`)
- **Short-lived clusters** — the SDK creates a RayCluster for the job and tears it down on completion
- **Integration with Kueue** for resource queueing and scheduling
- **Ray Dashboard** visibility for job monitoring and debugging

**Recommended for**

- **GRPO/RLVR training** with the verl backend (Ray-native, multi-GPU)
- **SFT, OSFT, and LoRA fine-tuning** via direct invocation on Ray
- Teams already using Ray for distributed workloads
- Workloads that benefit from Ray's actor-based distribution model

**Resource considerations**

- **GPU(s) required** on the Ray head pod (verl uses `STRICT_PACK` — all GPUs co-located)
- **No shared PVC required** for GRPO — the RayCluster is ephemeral; persist results to S3 or external storage
- **PVC recommended** for SFT/OSFT/LoRA — model and dataset stored on a PVC accessible from Ray pods
- The Workbench only submits and monitors the job

**Learn more**

- [SFT fine-tuning on Ray](sft_ray/README.md) — single GPU
- [OSFT continual learning on Ray](osft_ray/README.md) — single GPU
- [LoRA fine-tuning on Ray](lora_ray/README.md) — single GPU
- [GRPO fine-tuning on Ray](grpo_ray/README.md) — multi-node with verl

---

### Pipeline Mode (Automated Workflows)

**What it is**

Training is orchestrated as a **RHOAI pipeline** (based on Kubeflow Pipelines), which automates the end-to-end lifecycle:

- **Orchestrated training steps**:
  - Data preparation and validation
  - Fine-tuning (SFT, OSFT, or LoRA)
  - Evaluation and metrics collection
  - Model registration

**Recommended for**

- **Repeatable, production-oriented workflows**
  - Nightly or scheduled retraining
  - CI/CD-style evaluation on new data or code changes
- Teams that need:
  - Traceability (which data and code produced which model)
  - Approval flows (for example, only register models that meet SLA thresholds)
  - Easy re-runs with different hyperparameters or datasets

**Resource considerations**

- Similar to the distributed mode, shared storage and GPUs per training pod.

**Learn more**

- [Training Hub pipelines example](pipelines/training-hub/README.md)

---

## RHOAI Version Compatibility

These examples target specific versions of **Red Hat OpenShift AI**. To avoid confusion:

- **Root examples (this folder)**  
  - Reflect the **latest supported RHOAI version** for this repository.
  - Use current recommended runtimes, APIs, and best practices.

- **Version-specific subfolders** (for example, `rhoai-3.2/`)  
  - Contain **pinned versions** of the same examples adapted for that RHOAI release.
  - Capture differences in:
    - Runtime images
    - API fields (for example, `TrainJob`, `ClusterTrainingRuntime`)
    - Platform features and limitations

- **Per-example READMEs**
  - Each individual example has its own `README.md` that explicitly states:
    - **Verified RHOAI versions**
    - Any required operators (for example, Kubeflow Trainer, GPU Operator)
    - Known caveats or deviations from the latest syntax

When in doubt:

- Start with the **README in the specific example directory** you plan to run.
- If your cluster runs an older RHOAI version, check for a matching `rhoai-<version>/` variant of the example before adapting the latest one.
