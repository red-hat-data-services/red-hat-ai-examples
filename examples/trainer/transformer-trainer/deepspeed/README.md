# DeepSpeed Distributed Training with TransformersTrainer

This example demonstrates distributed fine-tuning using **DeepSpeed ZeRO optimization**.

DeepSpeed provides ZeRO (Zero Redundancy Optimizer), which partitions optimizer states, gradients, and optionally model parameters across GPUs to reduce memory usage. It also supports CPU offloading for training very large models.

This example fine-tunes **BERT-base** on the **IMDB** sentiment classification dataset with DeepSpeed ZeRO Stage 2.

## When to use DeepSpeed

| Strategy | Best for | Memory efficiency | Complexity |
| --- | --- | --- | --- |
| [DDP](../ddp/) | Models that fit in a single GPU | Low (full model copy per GPU) | Simplest |
| [FSDP](../fsdp/) | Large models that exceed single GPU memory | High (shards across GPUs) | Moderate |
| **DeepSpeed (this example)** | Very large models, advanced optimization | Highest (ZeRO stages) | More configuration |

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/trainer/transformer-trainer/deepspeed` and open the notebook.

## Key DeepSpeed configuration

### DeepSpeed config dict

The DeepSpeed config is defined as a Python dict inside `train_func()` and passed to `TrainingArguments(deepspeed=ds_config)`. It must be inside the training function because the function is serialized and executed in training pods.

```python
ds_config = {
    "bf16": {"enabled": "auto"},
    "fp16": {"enabled": "auto"},
    "zero_optimization": {
        "stage": 2,
        "overlap_comm": True,
        "contiguous_gradients": True,
        "reduce_bucket_size": 5e8,
    },
    "train_batch_size": "auto",
    "train_micro_batch_size_per_gpu": "auto",
    "gradient_accumulation_steps": "auto",
}
```

### ZeRO stages

DeepSpeed provides three ZeRO stages with increasing memory optimization:

| Stage | What it partitions | Offload support (optional) | Memory reduction | Communication overhead |
| --- | --- | --- | --- | --- |
| **Stage 1** | Optimizer states | Optimizer to CPU | ~4x | Same as data parallelism |
| **Stage 2** (this example) | Optimizer states + gradients | Optimizer to CPU | ~8x | Same as data parallelism |
| **Stage 3** | Optimizer states + gradients + parameters | Optimizer + parameters to CPU/NVMe | Linear with GPU count | 1.5x data parallelism |

This notebook uses **Stage 2**, which provides a good balance of memory savings and simplicity.

## Running the example

Open `deepspeed-trainer-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK, DeepSpeed, and required packages
2. **Configuring authentication and paths** -- API access + PVC mount paths
3. **Defining the training function** -- `transformers.Trainer` with DeepSpeed ZeRO config
4. **Staging model and dataset to the PVC** -- Download BERT-base + IMDB subset from the workbench
5. **Configuring and submitting TransformersTrainer** -- DeepSpeed training + checkpoints
6. **Monitoring progress** -- View progress in the OpenShift AI Dashboard
7. **Cleanup** -- Deleting the training job

## Customization

| Parameter | Default | Description |
| --- | --- | --- |
| `NUM_NODES` | 2 | Number of training nodes |
| `GPUS_PER_NODE` | 1 | GPUs per node |
| `MODEL_NAME` | `bert-base-uncased` | Any HuggingFace model |
| `DATASET_NAME` | `stanfordnlp/imdb` | Any HuggingFace dataset |
| `num_train_epochs` | 1 | Training epochs (in `train_func`) |
| `PVC_NAME` | `shared` | Update if you use a different PVC name |

## Troubleshooting

### DeepSpeed not found

If you see `ModuleNotFoundError: No module named 'deepspeed'`, ensure `deepspeed` is included in the install cell. The training pods must have DeepSpeed available in the runtime image.

### `/dev/shm` "No space left on device"

DeepSpeed creates multiple NCCL communicators whose proxy buffers can exceed the default 64MB `/dev/shm` in Kubernetes pods. The notebook uses `PodTemplateOverrides` to mount a larger memory-backed `/dev/shm`:

The notebook already includes this fix — see the `shm_override` variable in the configuration cell and the `options=[shm_override]` argument in the submit cell. This is not needed for DDP or FSDP, which create fewer NCCL communicators.

### NCCL errors

If you see NCCL timeout or connection errors:

```bash
oc logs <pod-name> -c node | grep -i "nccl"
```

Common fixes:

* Ensure all nodes can communicate on the required ports
* Check that the NCCL socket interface is correctly configured
* Increase `NCCL_TIMEOUT` if training steps are very long

### Out of memory

If you hit OOM with DeepSpeed:

* Reduce `per_device_train_batch_size` in `train_func`
* Reduce `max_length` in the tokenizer to shorten input sequences
