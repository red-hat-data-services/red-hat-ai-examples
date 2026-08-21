# Train from Extracted Data (TRAIN_ONLY) with SpeculativeDecodingTrainer

This example demonstrates how to train an Eagle3 draft model from pre-extracted hidden states using the `TRAIN_ONLY` mode of `SpeculativeDecodingTrainer`. No vLLM sidecar is needed -- the training container reads hidden state tensors directly from the PVC.

> **Prerequisite:** This notebook requires hidden states extracted by a completed [DATA_ONLY](../data-only/) run. Run the `data-only/` notebook first.

This example uses **Qwen3-0.6B** as the verifier model and trains from data extracted with the **ultrachat** dataset.

## When to use TRAIN_ONLY

| Mode | Best for | vLLM Required | Complexity |
| --- | --- | --- | --- |
| [DATA_ONLY](../data-only/) | Extract once, experiment many times | Managed sidecar or external | Low |
| **TRAIN_ONLY (this example)** | Iterate on hyperparameters without re-extracting | None | Low |
| [OFFLINE](../offline/) | Reuse an existing vLLM deployment | External (self-managed) | Moderate |
| [ONLINE](../online/) | Simplest end-to-end path | Managed sidecar | Simplest |

TRAIN_ONLY is designed for the second step of a two-step workflow. After extracting hidden states once with DATA_ONLY, you can run TRAIN_ONLY repeatedly with different hyperparameters (learning rate, epochs, scheduler, architecture choices) without re-running the expensive extraction step. This makes hyperparameter tuning significantly faster and cheaper.

**Trade-off:** TRAIN_ONLY requires a prior DATA_ONLY run and depends on its output paths. If you only need a single end-to-end run, [ONLINE](../online/) mode is simpler. If you want extraction and training in one job with an external vLLM server, use [OFFLINE](../offline/) mode.

## How TRAIN_ONLY Works

1. The trainer reads pre-extracted hidden state tensors from `hidden_states_path` on the PVC
2. The preprocessed dataset is loaded from `data_path` (the DATA_ONLY output directory)
3. The Eagle3 draft model is initialized and trained on the hidden states
4. Checkpoints are saved to `output_dir` at the frequency specified by `checkpoint_freq`
5. The final trained draft model is saved to `output_dir`

Since no vLLM server is involved, TRAIN_ONLY jobs require only the training container's GPU allocation (typically 2 GPUs). This makes TRAIN_ONLY the most resource-efficient mode for iterative experimentation.

## What Gets Trained

Only the draft model's small components are trained — the verifier model is frozen and never modified:

- **FC layer 1 (fusion):** Combines hidden states from four verifier layers into one vector
- **FC layer 2 (concat):** Merges the fused hidden state with the previous token's embedding
- **One Transformer decoder layer:** Predicts the next token probability distribution

The draft model is very small (~1.2 GB with Qwen3-0.6B), making training fast and memory-efficient.

## Hardware Requirements

The table below shows the **minimum** resources needed with Qwen3-0.6B. The notebook defaults to minimum values with recommended settings in comments.

| Component | GPU (min) | GPU (rec.) | CPU (min) | CPU (rec.) | Memory (min) | Memory (rec.) |
| --- | --- | --- | --- | --- | --- | --- |
| Training container | 1 | 2 | 1 core | 4 cores | 32Gi | 64Gi |

- 1 GPU works but is slower — 2 GPUs enable data-parallel training
- No vLLM sidecar or external server is needed — TRAIN_ONLY reads directly from the PVC

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/fine-tuning/rhoai-3.6/speculator/train-only` and open `speculator-train-only-example.ipynb`.

### Prerequisites

Before running TRAIN_ONLY, ensure:

1. You have completed a [DATA_ONLY](../data-only/) run and it finished successfully
2. The DATA_ONLY output directory exists on the PVC and contains:
   - `hidden_states/` — Extracted hidden state tensors (`.safetensors` files)
   - Preprocessed dataset files
3. You know the exact PVC URI of the DATA_ONLY output directory (this becomes `data_path` and `hidden_states_path`)

### ClusterTrainingRuntime (CTR)

TRAIN_ONLY mode uses the `speculator-model-opt-cuda` CTR. This CTR provisions only the training container — no vLLM sidecar is included since TRAIN_ONLY works entirely from pre-extracted hidden states. This is the same CTR used by OFFLINE mode and DATA_ONLY with External vLLM.

The CTR must be pre-installed on your cluster. The notebook verifies its existence before job submission.

## Verifier Model

Even though TRAIN_ONLY does not run inference, it still requires the `verifier_model` parameter. The SDK uses the model configuration to initialize the draft model architecture — the draft model's dimensions must match the verifier's hidden state sizes.

| Input Type | Example | `target_layer_ids` |
| --- | --- | --- |
| **HuggingFace ID** | `"Qwen/Qwen3-0.6B"` | Auto-computed as `[2, n//2, n-3, n]` where `n` is the number of hidden layers |
| **PVC URI** | `"pvc://shared/models/Qwen3-0.6B"` | Must be provided explicitly — SDK cannot read model config from PVC |

The training pods download the model automatically when using a HuggingFace ID. Pass your HuggingFace token via the `env` parameter to authenticate.

## Key TRAIN_ONLY Configuration

The key parameters specific to TRAIN_ONLY mode:

```python
train_only_trainer = SpeculativeDecodingTrainer(
    mode=SpeculatorMode.TRAIN_ONLY,
    speculator_type=SpeculatorType.EAGLE3,
    verifier_model=VERIFIER_MODEL,
    hidden_states_path=f"{DATA_ONLY_OUTPUT}/hidden_states",
    data_path=DATA_ONLY_OUTPUT,
    training_resources=TRAINING_RESOURCES,
    epochs=EPOCHS,
    lr=LEARNING_RATE,
    total_seq_len=TOTAL_SEQ_LEN,
    output_dir=TRAIN_ONLY_OUTPUT,
    config=SpeculatorConfig(
        target_layer_ids=TARGET_LAYER_IDS,
        num_layers=1,
        ttt_steps=3,
        norm_before_residual=True,
        scheduler_type="linear",
        checkpoint_freq=1.0,
        resume_from_checkpoint=True,
    ),
    env={"HF_TOKEN": HF_TOKEN},
    # ...
)
```

### Path Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `hidden_states_path` | PVC URI | Path to the `hidden_states/` subdirectory from a DATA_ONLY run. Contains the `.safetensors` files with extracted hidden state tensors. |
| `data_path` | PVC URI | Path to the DATA_ONLY output directory. Contains the preprocessed dataset files needed for training. |
| `output_dir` | PVC URI | Where training checkpoints and the final draft model are saved. Use a different path from the DATA_ONLY output to keep extraction data and training results separate. |

### Training Hyperparameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `epochs` | — | Integer | Number of full passes over the training data. Start with 3 and increase if the model hasn't converged. |
| `lr` | — | Float | AdamW learning rate. `1e-4` is a good starting point for Eagle3. Smaller values (e.g., `5e-5`) may give better results with more epochs. |
| `total_seq_len` | — | Integer | Maximum sequence length. Should match the value used during DATA_ONLY extraction. |

### SpeculatorConfig Parameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `target_layer_ids` | Auto-computed | List[int] | Must match the layers used during DATA_ONLY extraction. If the DATA_ONLY run auto-computed them from a HuggingFace ID, use the same model ID here so the SDK computes the same values. |
| `num_layers` | `1` | Integer | Number of Transformer decoder layers in the draft model. The default of 1 is standard for Eagle3. Increasing this adds model capacity but also increases draft model size and inference latency. |
| `ttt_steps` | — | Integer | Test-time training steps per batch. Controls how many gradient steps are taken on each mini-batch. |
| `norm_before_residual` | — | Boolean | Apply LayerNorm before the residual connection in the draft model's decoder layer. |
| `scheduler_type` | `"linear"` | String | Learning rate scheduler. `"linear"` decays the learning rate linearly to zero over the training run. |
| `checkpoint_freq` | `1.0` | Float | Save a checkpoint every N epochs. `1.0` saves after every epoch. `0.5` saves twice per epoch. |
| `resume_from_checkpoint` | `False` | Boolean | Resume training from the last saved checkpoint in `output_dir`. Restores model weights, optimizer state, and epoch count. Set to `True` when re-running a job that was interrupted. |

### Resource Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `training_resources` | Dict | GPU/CPU/memory for the training container. Minimum: `{"nvidia.com/gpu": 1, "cpu": "1", "memory": "32Gi"}`. Recommended: `{"nvidia.com/gpu": 2, "cpu": "4", "memory": "64Gi"}` (2 GPUs enable data-parallel training). |

TRAIN_ONLY does not use `vllm_resources` or `vllm_endpoint` — there is no vLLM server involved.

## Checkpoint Resumption

The `resume_from_checkpoint` parameter in `SpeculatorConfig` is particularly useful for TRAIN_ONLY because you may want to:

- **Recover from failures:** If a training pod is preempted or times out, set `resume_from_checkpoint=True` and resubmit. The trainer picks up from the last saved checkpoint.
- **Extend training:** If initial training wasn't enough, increase `epochs` and resubmit with `resume_from_checkpoint=True`. The trainer continues from where it left off rather than restarting from epoch 0.
- **Avoid redundant work:** If a completed run is resubmitted (e.g., accidentally), `resume_from_checkpoint=True` lets the trainer detect that all epochs are done and skip redundant training.

When resuming, if an `interrupted` checkpoint directory exists (from a crash mid-save), it is automatically cleaned up before training continues.

## Running the Example

Open `speculator-train-only-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK and required packages
2. **Configuring authentication and paths** -- API access, PVC mount paths, and model configuration
3. **Setting the DATA_ONLY output path** -- Point to the output from your completed DATA_ONLY run
4. **Configuring the TRAIN_ONLY trainer** -- Set up training parameters, hidden states path, and output
5. **Submitting the TrainJob** -- Launch the training job on the cluster
6. **Monitoring progress** -- Check job status and view logs
7. **Cleanup** -- Delete the TrainJob when training is complete

## Iterating on Hyperparameters

TRAIN_ONLY's main advantage is fast iteration. Here are common experiments to try:

| Experiment | What to change | Expected effect |
| --- | --- | --- |
| More training | Increase `epochs` from 3 to 10 | Higher acceptance rate, diminishing returns past ~10 |
| Lower learning rate | Decrease `lr` from `1e-4` to `5e-5` | Smoother convergence, may need more epochs |
| Longer sequences | Increase `total_seq_len` from 2048 to 4096 | Better long-context performance, more memory needed |
| More draft layers | Increase `num_layers` from 1 to 2 | Higher accuracy but larger/slower draft model |

For each experiment, change `RUN_NAME` (or `output_dir`) to keep results separate on the PVC. All experiments reuse the same hidden state data from your DATA_ONLY run.

## Full Parameter Reference

### SpeculativeDecodingTrainer Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `mode` | `SpeculatorMode.TRAIN_ONLY` | Must be set to `TRAIN_ONLY` for this mode |
| `speculator_type` | `SpeculatorType.EAGLE3` | Draft model architecture (currently only Eagle3 is supported) |
| `verifier_model` | String | HuggingFace model ID or PVC URI of the verifier model |
| `hidden_states_path` | PVC URI | Path to the `hidden_states/` subdirectory from a DATA_ONLY run |
| `data_path` | PVC URI | Path to the DATA_ONLY output directory |
| `training_resources` | Dict | GPU/CPU/memory for the training container |
| `epochs` | Integer | Number of full passes over the training data |
| `lr` | Float | AdamW learning rate |
| `total_seq_len` | Integer | Maximum sequence length |
| `output_dir` | PVC URI | Directory for checkpoints and final draft model |
| `enable_progression_tracking` | Boolean | Enable SDK-side progress polling |
| `packages_to_install` | List[str] | Additional Python packages to install in the training pod |
| `env` | Dict | Environment variables passed to training pods (e.g., `{"HF_TOKEN": "..."}`) |

### Not Used in TRAIN_ONLY

The following parameters are not applicable to TRAIN_ONLY mode:

| Parameter | Why |
| --- | --- |
| `dataset_name` | TRAIN_ONLY reads from `data_path`, not a raw dataset |
| `vllm_resources` | No vLLM sidecar is deployed |
| `vllm_endpoint` | No vLLM server is used |
| `vllm_gpu_memory_utilization` | No vLLM sidecar is deployed |
| `regenerate_responses` | No data generation step |

## Troubleshooting

### Hidden states not found

If the job fails with a missing path error:

- Verify the `DATA_ONLY` run completed successfully
- Check that `DATA_ONLY_OUTPUT` matches the output path used in the DATA_ONLY run
- Ensure the `hidden_states/` subdirectory exists on the PVC
- From your workbench, verify the files: `ls /opt/app-root/src/<pvc-name>/speculator/<run-name>/hidden_states/`

### Resuming from checkpoint

If training was interrupted:

- Set `resume_from_checkpoint=True` in `SpeculatorConfig`
- The trainer will automatically find the latest checkpoint in `output_dir`
- Resubmit the job with the same configuration
- If the job still fails, check for an `interrupted` checkpoint directory that may need manual cleanup

### Target layer mismatch

If training errors mention layer dimension mismatches:

- Verify `target_layer_ids` match exactly the layers used during the DATA_ONLY extraction
- If DATA_ONLY used auto-detected layers, use the same HuggingFace model ID in TRAIN_ONLY so the SDK computes the same values
- If DATA_ONLY used explicit layers, copy those exact values into TRAIN_ONLY's `SpeculatorConfig`

### Out of GPU memory

If the training container runs out of memory:

- Reduce `total_seq_len` to lower memory usage
- Ensure `training_resources` has enough GPU memory (64Gi recommended for Qwen3-0.6B)
- Check that no other workloads are competing for GPU resources on the node
