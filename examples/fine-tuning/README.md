# Fine-tuning Examples Overview

This directory contains end-to-end examples for fine-tuning large language models on Red Hat OpenShift AI (RHOAI).

All examples are built primarily on top of **Training Hub** algorithms running on the RHOAI platform, currently:

- **SFT (Supervised Fine-Tuning)**
- **OSFT (Orthogonal Subspace Fine-Tuning)**
- **LoRA + SFT (Low-Rank Adaptation)**

For detailed algorithm documentation and configuration options, see the upstream [Training Hub documentation](https://github.com/Red-Hat-AI-Innovation-Team/training_hub/tree/main).

---

## Execution Modes

There are three ways to run fine tuning examples:

1. **Local mode (Workbench-only)**
2. **Distributed mode (Kubeflow Trainer)**
3. **Pipeline mode (automated training, model evaluation, and registration with Kubeflow Pipelines)**

### Local Mode (Workbench-only)

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

- [SFT fine-tuning example](training-hub/sft/README.md)
- [OSFT fine-tuning example](osft/README.md)

---

### Distributed Mode (Kubeflow Trainer)

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

- [SFT fine-tuning example](training-hub/sft/README.md)
- [OSFT fine-tuning example](osft/README.md)

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
