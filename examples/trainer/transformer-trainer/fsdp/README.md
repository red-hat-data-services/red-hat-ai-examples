# FSDP Distributed Training with TransformersTrainer

This example demonstrates distributed fine-tuning using **Fully Sharded Data Parallel (FSDP)**.

FSDP shards model parameters, gradients, and optimizer states across all participating GPUs. Unlike DDP (which replicates the full model on each GPU), FSDP significantly reduces per-GPU memory usage, enabling training of models that are too large to fit in a single GPU's memory.

This example fine-tunes **BERT-base** on the **IMDB** sentiment classification dataset with FSDP full sharding and sharded checkpointing.

## When to use FSDP

| Strategy | Best for | Memory efficiency | Complexity |
| --- | --- | --- | --- |
| [DDP](../ddp/) | Models that fit in a single GPU | Low (full model copy per GPU) | Simplest |
| **FSDP (this example)** | Large models that exceed single GPU memory | High (shards across GPUs) | Moderate |
| [DeepSpeed](../deepspeed/) | Very large models, advanced optimization | Highest (ZeRO stages) | More configuration |

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/trainer/transformer-trainer/fsdp` and open the notebook.

## Key FSDP configuration

### FSDP in TrainingArguments

FSDP is configured directly in `TrainingArguments` inside the training function:

```python
training_args = TrainingArguments(
    ...
    fsdp="full_shard auto_wrap",
    fsdp_config={
        "activation_checkpointing": True,
        "sync_module_states": True,
        "use_orig_params": True,
        "limit_all_gathers": False,
    },
)
```

### Checkpoint state dict mode

The notebook includes a `USE_SHARDED_STATE_DICT` toggle to switch between two checkpoint modes:

| Mode | File format | Best for |
| --- | --- | --- |
| **Sharded** (`True`, default) | `pytorch_model_fsdp_0`, `optimizer_0` (per-rank shards) | Large models, faster I/O |
| **Full state** (`False`) | `pytorch_model_fsdp.bin`, `optimizer.bin` (single file) | Simpler, easier to load outside FSDP |

> **Important:** Do not switch modes mid-training. If you change this setting, delete existing checkpoints first.

### FSDP sharding strategies

| Strategy | What it shards | Use case |
| --- | --- | --- |
| `full_shard` (this example) | Parameters + gradients + optimizer states | Maximum memory savings |
| `shard_grad_op` | Gradients + optimizer states only | Less communication overhead |
| `hybrid_shard` | Full shard within node, replicate across nodes | Multi-node with fast intra-node interconnect |

### Activation checkpointing

Setting `activation_checkpointing: True` in `fsdp_config` trades compute for memory by recomputing activations during the backward pass instead of storing them. This further reduces memory usage at the cost of ~20-30% more compute time.

## Running the example

Open `fsdp-trainer-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK and required packages
2. **Configuring authentication and paths** -- API access + PVC mount paths
3. **Defining the training function** -- `transformers.Trainer` with FSDP and sharded checkpointing
4. **Staging model and dataset to the PVC** -- Download BERT-base + IMDB subset from the workbench
5. **Configuring and submitting TransformersTrainer** -- FSDP training + checkpoints
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
| `fsdp` | `full_shard auto_wrap` | FSDP sharding strategy |
| `USE_SHARDED_STATE_DICT` | `True` | Sharded vs full state checkpointing |
| `PVC_NAME` | `shared` | Update if you use a different PVC name |

## Troubleshooting

### NCCL errors

If you see NCCL timeout or connection errors:

```bash
oc logs <pod-name> -c node | grep -i "nccl"
```

Common fixes:

* Ensure all nodes can communicate on the required ports
* Check that the NCCL socket interface is correctly configured
* Increase `NCCL_TIMEOUT` if training steps are very long

### Out of memory with FSDP

If you hit OOM even with FSDP:

* Reduce `per_device_train_batch_size` in `train_func`
* Ensure `activation_checkpointing` is enabled in `fsdp_config`
* Try `shard_grad_op` strategy if `full_shard` communication overhead is too high

### Checkpoint format mismatch

If you see `FileNotFoundError: pytorch_model_fsdp.bin` or similar when resuming:

You switched between sharded and full state modes. Delete existing checkpoints first:

```bash
rm -rf /opt/app-root/src/shared/checkpoints/fsdp-trainer/checkpoint-*
```
