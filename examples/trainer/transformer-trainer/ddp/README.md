# DDP Distributed Training with TransformersTrainer

This example demonstrates distributed fine-tuning using **PyTorch DistributedDataParallel (DDP)**.

DDP replicates the entire model on each GPU and synchronizes gradients after every backward pass. It is the simplest distributed training strategy and works well when the model fits comfortably in a single GPU's memory.

This example fine-tunes **DistilBERT** on the **IMDB** sentiment classification dataset.

## When to use DDP

| Strategy | Best for | Memory efficiency | Complexity |
| --- | --- | --- | --- |
| **DDP (this example)** | Models that fit in a single GPU | Low (full model copy per GPU) | Simplest |
| [FSDP](../fsdp/) | Large models that exceed single GPU memory | High (shards across GPUs) | Moderate |
| [DeepSpeed](../deepspeed/) | Very large models, advanced optimization | Highest (ZeRO stages) | More configuration |

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/trainer/transformer-trainer/ddp` and open the notebook.

## Key DDP configuration

The DDP strategy is the default. The key setting in `TrainingArguments` is:

```python
training_args = TrainingArguments(
    ...
    ddp_find_unused_parameters=False,
)
```

## Running the example

Open `ddp-trainer-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK and required packages
2. **Configuring authentication and paths** -- API access + PVC mount paths
3. **Staging model and dataset to the PVC** -- Download DistilBERT + an IMDB subset from the workbench
4. **Defining the training function** -- A `transformers.Trainer` training loop that loads inputs from the PVC
5. **Configuring and submitting TransformersTrainer** -- Distributed training + `output_dir="pvc://..."` for persisted checkpoints
6. **Monitoring progress** -- View progress in the OpenShift AI Dashboard (**Training Jobs**)
7. **Cleanup** -- Deleting the training job

## Customization

| Parameter | Default | Description |
| --- | --- | --- |
| `NUM_NODES` | 2 | Number of training nodes |
| `GPUS_PER_NODE` | 1 | GPUs per node |
| `MODEL_NAME` | `distilbert-base-uncased` | Any HuggingFace model |
| `DATASET_NAME` | `stanfordnlp/imdb` | Any HuggingFace dataset |
| `num_train_epochs` | 1 | Training epochs (in `train_func`) |
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

### Out of memory

If you hit OOM with DDP, the model may be too large for a single GPU. Consider switching to [FSDP](../fsdp/) or [DeepSpeed](../deepspeed/) which shard the model across GPUs.
