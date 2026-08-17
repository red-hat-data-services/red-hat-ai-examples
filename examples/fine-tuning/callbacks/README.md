# Training Hub Callbacks on Red Hat OpenShift AI

This example demonstrates using unified Training Hub callbacks when submitting TrainJobs with `TrainingHubTrainer` from the Kubeflow SDK on Red Hat OpenShift AI.

## Note

This example is compatible with RHOAI **3.6.EA1+**. Unified Training Hub callbacks are not available on earlier RHOAI releases.

## Overview

Training Hub provides a unified callback interface (`TrainingHubCallback`) that works across InstructLab Training, Mini-Trainer, and Unsloth backends. The Kubeflow SDK exposes this through `TrainingHubTrainer(..., callbacks=[MyCallback])`.

The SDK:

1. **Validates** callback classes at submit time (before the pod starts)
2. **Serializes** callback source code into the training pod script
3. **Injects** callbacks into Training Hub entry points: `sft`, `osft`, `lora_sft`, `lora_grpo`

You define the callback once. The same class runs on any supported backend without backend-specific rewrites.

## Supported Backends

| Backend | Algorithm | Training Hub API |
|---------|-----------|------------------|
| Unsloth | LoRA SFT | `lora_sft` |
| InstructLab Training | SFT | `sft` |
| Mini-Trainer | OSFT | `osft` |

## Hardware Requirements

| Backend | Nodes | GPU/node | GPU Type | CPU | Memory |
|---------|-------|----------|----------|-----|--------|
| Unsloth (LoRA SFT) | 1 | 1 | NVIDIA L40/L40S or equivalent | 4 cores | 16Gi |
| InstructLab (SFT) | 1 | 1 | NVIDIA L40/L40S or equivalent | 4 cores | 16Gi |
| Mini-Trainer (OSFT) | 1 | 1 | NVIDIA L40/L40S or equivalent | 4 cores | 16Gi |

## Prerequisites

- OpenShift cluster with OpenShift AI (**RHOAI 3.6.EA1+**) and the **trainer** component enabled
- `training-hub` ClusterTrainingRuntime available in the cluster
- Kubeflow SDK with `callbacks=` support
- `training_hub` with unified callbacks

### Installing Training Hub from source

Until the cluster runtime image ships unified callbacks, install from source via `packages_to_install`:

```python
packages_to_install=[
    "git+https://github.com/Red-Hat-AI-Innovation-Team/training_hub.git@main",
]
```

For OSFT, also install Mini-Trainer from source:

```python
packages_to_install=[
    "git+https://github.com/Red-Hat-AI-Innovation-Team/training_hub.git@main",
    "git+https://github.com/Red-Hat-AI-Innovation-Team/mini_trainer.git@main",
]
```

## Quick Start

### 1. Define a Callback (in a `.py` file)

```python
from training_hub import TrainingHubCallback, TrainingHubContext


class LossLogger(TrainingHubCallback):
    def on_train_begin(self, context: TrainingHubContext) -> None:
        print(f"Training started — output_dir={context.output_dir}", flush=True)

    def on_log(self, context: TrainingHubContext) -> None:
        print(f"step={context.step} loss={context.loss} lr={context.learning_rate}", flush=True)

    def on_train_end(self, context: TrainingHubContext) -> None:
        print(f"Training finished — step={context.step}", flush=True)
```

> Callbacks **must** be in a `.py` file (not inline in a notebook). The SDK uses `inspect.getsource()`.

### 2. Submit a TrainJob

```python
from kubeflow.trainer import TrainerClient
from kubeflow.trainer.rhai import TrainingHubAlgorithms, TrainingHubTrainer

from my_callbacks import LossLogger

# Same LossLogger works with any supported algorithm:
# SFT, OSFT, LORA_SFT, LORA_GRPO
trainer = TrainingHubTrainer(
    algorithm=TrainingHubAlgorithms.LORA_SFT,
    func_args={
        "model_path": "Qwen/Qwen2.5-0.5B-Instruct",
        "data_path": "/data/train.jsonl",
        "ckpt_output_dir": "/tmp/out",
        "num_epochs": 1,
    },
    callbacks=[LossLogger],
    resources_per_node={"cpu": "4", "memory": "16Gi", "nvidia.com/gpu": "1"},
    packages_to_install=[
        "git+https://github.com/Red-Hat-AI-Innovation-Team/training_hub.git@main",
    ],
)

job_name = TrainerClient().train(runtime="training-hub", trainer=trainer)
```

Pass **classes**, not instances: `callbacks=[LossLogger]`.

### 3. Verify in Pod Logs

```text
[Kubeflow] Prepared 1 Training Hub callback(s)
[Kubeflow] Training Hub callback injection configured
Training started — output_dir=/tmp/out
step=1 loss=2.34 lr=0.0001
...
Training finished — step=100
```

## Callback Rules

- Must subclass `TrainingHubCallback`
- Must have a no-argument constructor
- Must be self-contained (no module-level dependencies outside the class)
- Only the 9 unified hooks are supported (see table below)

## Supported Hooks

| Hook | When it fires |
|------|---------------|
| `on_train_begin` | After init, before training loop |
| `on_epoch_begin` | Start of each epoch |
| `on_step_begin` | Start of each step |
| `on_log` | Metrics are logged |
| `on_evaluate` | After evaluation |
| `on_save` | After checkpoint saved |
| `on_step_end` | End of each step |
| `on_epoch_end` | End of each epoch |
| `on_train_end` | Training completes |

## Running the Example Notebook

The included notebook (`training_hub_callbacks_smoke.ipynb`) runs six TrainJobs — with and without callbacks — across all three backends:

```bash
jupyter notebook training_hub_callbacks_smoke.ipynb
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `callbacks` not on `TrainingHubTrainer` | Upgrade SDK to a version with callbacks support |
| SDK markers OK, no hook output | Verify `training_hub` version has callbacks |
| OSFT crashes `is_main_process` | Add `mini_trainer@main` to `packages_to_install` |
| `inspect.getsource` error | Move callback to a `.py` file |
| `defines unsupported hooks` | Remove non-unified hook methods |
| `must use a no-argument constructor` | Remove required `__init__` params |

## Links

| Resource | Link |
|----------|------|
| Training Hub | [Red-Hat-AI-Innovation-Team/training_hub](https://github.com/Red-Hat-AI-Innovation-Team/training_hub) |
| Kubeflow SDK | [opendatahub-io/kubeflow-sdk](https://github.com/opendatahub-io/kubeflow-sdk) |
