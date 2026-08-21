# Online Mode (End-to-End Managed) with SpeculativeDecodingTrainer

This example demonstrates how to train an Eagle3 draft model using the `ONLINE` mode of `SpeculativeDecodingTrainer`. This is the simplest workflow -- the SDK manages everything in a single job:

1. Deploys a vLLM sidecar to serve the verifier model
2. Extracts hidden states from the dataset batch by batch
3. Trains the Eagle3 draft model using the extracted hidden states

Hidden states are processed in a streaming fashion -- each batch is extracted, used for training, then discarded. This means disk usage stays constant regardless of dataset size.

This example uses **Qwen3-0.6B** as the verifier model and the `magpie` built-in dataset.

## When to use ONLINE

| Mode | Best for | vLLM Required | Complexity |
| --- | --- | --- | --- |
| [DATA_ONLY](../data-only/) | Extract once, experiment many times | Managed sidecar or external | Low |
| [TRAIN_ONLY](../train-only/) | Iterate on hyperparameters without re-extracting | None | Low |
| [OFFLINE](../offline/) | Reuse an existing vLLM deployment | External (self-managed) | Moderate |
| **ONLINE (this example)** | Simplest end-to-end path | Managed sidecar | Simplest |

ONLINE mode is the recommended starting point when you want the simplest possible experience. Everything is handled in one job — the SDK deploys the vLLM sidecar, extracts hidden states, trains the draft model, and saves the result. No external infrastructure is required beyond the cluster itself.

**Trade-offs:**

- **vs. DATA_ONLY + TRAIN_ONLY:** ONLINE is simpler (one job instead of two), but you cannot reuse the extracted data for multiple training runs with different hyperparameters. If you plan to experiment with hyperparameters, use [DATA_ONLY](../data-only/) + [TRAIN_ONLY](../train-only/) instead.
- **vs. OFFLINE:** ONLINE manages the vLLM server automatically, while OFFLINE lets you bring your own vLLM deployment with custom configuration. ONLINE is simpler but less flexible.
- **Resource cost:** ONLINE requires the most GPUs of any mode (3 total: 2 for training + 1 for the vLLM sidecar) because both containers run simultaneously.

## How ONLINE Works

1. The SDK deploys a vLLM sidecar container alongside the training container in the same pod
2. The vLLM sidecar loads the verifier model and begins serving
3. The SDK waits for the vLLM sidecar to become ready (up to `vllm_readiness_timeout_minutes`, default: 60 minutes)
4. The dataset is preprocessed and tokenized
5. If `regenerate_responses=True`, fresh on-policy responses are generated from the dataset prompts using the sidecar
6. Hidden states are extracted batch by batch from the vLLM sidecar and used immediately for training
7. Training progresses through all epochs, saving checkpoints at the frequency specified by `checkpoint_freq`
8. The final trained draft model is saved to `output_dir`
9. The vLLM sidecar is automatically cleaned up when the job completes

The streaming approach means hidden states are not persisted to disk — each batch is extracted, used for training, then discarded. This keeps disk usage constant but means the extraction work cannot be reused for future training runs.

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/fine-tuning/rhoai-3.6/speculator/online` and open `speculator-online-example.ipynb`.

### ClusterTrainingRuntime (CTR)

ONLINE mode uses the `vllm-extract-cuda` CTR, which provisions both the training container and the vLLM sidecar in a single pod. This is the same CTR used by DATA_ONLY with Managed Sidecar — it includes both the training runtime and the vLLM serving runtime.

The CTR must be pre-installed on your cluster. The notebook verifies its existence before job submission.

### Hardware Requirements

ONLINE mode requires the most GPUs because both the training container and the vLLM sidecar run simultaneously. The table below shows minimum and recommended resources for Qwen3-0.6B:

| Component | GPU (min) | GPU (rec.) | CPU (min) | CPU (rec.) | Memory (min) | Memory (rec.) |
| --- | --- | --- | --- | --- | --- | --- |
| Training container | 1 | 2 | 1 core | 4 cores | 32Gi | 64Gi |
| vLLM sidecar | 1 | 1 | 1 core | 4 cores | 48Gi | 96Gi |
| **Total** | **2** | **3** | **2 cores** | **8 cores** | **80Gi** | **160Gi** |

- The vLLM sidecar is hard-limited to exactly **1 GPU** — more raises a `ValueError`
- 1 training GPU works but is slower — 2 GPUs enable data-parallel training
- All GPUs must be on the same node

## Verifier Model

The `verifier_model` parameter specifies the large language model loaded into the vLLM sidecar for hidden state extraction. It accepts two input types:

| Input Type | Example | `target_layer_ids` |
| --- | --- | --- |
| **HuggingFace ID** | `"Qwen/Qwen3-0.6B"` | Auto-computed as `[2, n//2, n-3, n]` where `n` is the number of hidden layers |
| **PVC URI** | `"pvc://shared/models/Qwen3-0.6B"` | Must be provided explicitly — SDK cannot read model config from PVC |

When using a HuggingFace ID, the training pods download the model automatically during the job. Pass your HuggingFace token via the `env` parameter (`{"HF_TOKEN": HF_TOKEN}`) to authenticate, especially for gated models. Even for non-gated models like Qwen3-0.6B, a token is recommended to avoid rate limits.

Direct filesystem paths (e.g., `/mnt/models/...`) are **not supported** — training runs inside Kubernetes pods where local paths from the user's machine do not exist.

## Dataset

The `dataset_name` parameter specifies which dataset to use for hidden state extraction and training. It accepts multiple input types:

| Input Type | Example | Description |
| --- | --- | --- |
| **Built-in name** | `"ultrachat"`, `"magpie"`, `"gsm8k"` | Downloaded automatically during the job |
| **PVC URI** | `"pvc://shared/datasets/custom.jsonl"` | Self-provided JSON/JSONL file on the PVC — requires `regenerate_responses=False` |

The `max_samples` parameter caps how many samples are processed. The `total_seq_len` parameter sets the maximum sequence length for tokenization.

## Target Layer IDs

Eagle3 reads hidden states from exactly **4 intermediate layers** of the verifier model. These layers are chosen to give the draft model a spread of representations:

- **Early layer** — captures low-level token features
- **Middle layer** — captures mid-level semantic patterns
- **Late layer** — captures high-level reasoning
- **Final layer** — provides the target distribution for training

For Qwen3-0.6B (28 hidden layers), the auto-computed formula `[2, n//2, n-3, n]` gives `[2, 14, 25, 28]`.

When using a PVC URI for `verifier_model`, you **must** provide `target_layer_ids` explicitly via `SpeculatorConfig(target_layer_ids=[...])` because the SDK cannot access the model configuration file from the PVC at validation time. The SDK validates that exactly 4 IDs are provided — fewer or more raises a `ValueError`.

## Key ONLINE Configuration

The key parameters specific to ONLINE mode:

```python
online_trainer = SpeculativeDecodingTrainer(
    mode=SpeculatorMode.ONLINE,
    speculator_type=SpeculatorType.EAGLE3,
    verifier_model=VERIFIER_MODEL,
    dataset_name="magpie",
    max_samples=MAX_SAMPLES,
    total_seq_len=TOTAL_SEQ_LEN,
    vllm_resources=VLLM_RESOURCES,  # GPU/CPU/memory for the managed sidecar
    vllm_gpu_memory_utilization=0.9,
    training_resources=TRAINING_RESOURCES,  # GPU/CPU/memory for the training container
    regenerate_responses=True,
    epochs=EPOCHS,
    lr=LEARNING_RATE,
    output_dir=OUTPUT,
    config=SpeculatorConfig(
        target_layer_ids=TARGET_LAYER_IDS,
        resume_from_checkpoint=True,
    ),
    env={"HF_TOKEN": HF_TOKEN},
    # ...
)
```

### Resource Parameters

ONLINE mode requires **both** `vllm_resources` and `training_resources` since the vLLM sidecar and training container run simultaneously:

| Parameter | Type | Description |
| --- | --- | --- |
| `vllm_resources` | Dict | GPU/CPU/memory for the managed vLLM sidecar. The sidecar currently supports only **1 GPU** — providing more raises a `ValueError`. Minimum: `{"nvidia.com/gpu": 1, "cpu": "1", "memory": "48Gi"}`. Recommended: `{"nvidia.com/gpu": 1, "cpu": "4", "memory": "96Gi"}` |
| `vllm_gpu_memory_utilization` | Float (0.0–1.0) | Fraction of GPU memory the vLLM sidecar can use. Default is 0.9 (90%). Lower this if you encounter OOM errors during model loading. |
| `training_resources` | Dict | GPU/CPU/memory for the training container. Minimum: `{"nvidia.com/gpu": 1, "cpu": "1", "memory": "32Gi"}`. Recommended: `{"nvidia.com/gpu": 2, "cpu": "4", "memory": "64Gi"}` (2 GPUs enable data-parallel training). |

### Training Hyperparameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `epochs` | `3` | Integer | Number of full passes over the training data. Start with 3 and increase if the model hasn't converged. |
| `lr` | `1e-4` | Float | AdamW learning rate. `1e-4` is a good starting point for Eagle3. |
| `total_seq_len` | `2048` | Integer | Maximum sequence length for extraction and training |
| `max_samples` | All | Integer | Maximum number of dataset samples to process |

### SpeculatorConfig Parameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `target_layer_ids` | Auto-computed | List[int] | 4 transformer layer IDs for hidden state extraction. Auto-detected from HuggingFace model config; must be explicit for PVC URI models. |
| `num_layers` | `1` | Integer | Number of Transformer decoder layers in the draft model |
| `ttt_steps` | `3` | Integer | Test-time training steps per batch |
| `norm_before_residual` | `True` | Boolean | Apply LayerNorm before the residual connection |
| `scheduler_type` | `"linear"` | String | Learning rate scheduler: `"linear"`, `"cosine"`, or `"none"` |
| `checkpoint_freq` | `1.0` | Float | Save a checkpoint every N epochs |
| `save_best` | `False` | Boolean | Save only the best checkpoint by validation loss |
| `log_freq` | `1` | Integer | Logging frequency in training steps |
| `datagen_concurrency` | `4` | Integer | Number of concurrent vLLM extraction requests |
| `hidden_states_dtype` | `"bfloat16"` | String | Data type for hidden states: `"bfloat16"`, `"float16"`, or `"float32"` |
| `resume_from_checkpoint` | `False` | Boolean | Resume training from the last saved checkpoint. Note: in ONLINE mode, data preparation steps (response regeneration, preprocessing) still re-run on resume — only the training step is skipped if already completed. |

### Additional Trainer Parameters

These parameters are set directly on `SpeculativeDecodingTrainer(...)`, not inside `SpeculatorConfig`:

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `regenerate_responses` | `False` | Boolean | Generate fresh on-policy responses from prompts before extraction |

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `vllm_readiness_timeout_minutes` | `60` | Integer | How long to wait for the vLLM sidecar to become ready (minimum: 1 minute). Increase this for larger models that take longer to load. |
| `enable_progression_tracking` | `True` | Boolean | Enable SDK-side progress polling |
| `packages_to_install` | — | List[str] | Additional Python packages to install in the training pod |
| `env` | — | Dict | Environment variables passed to training pods (e.g., `{"HF_TOKEN": "..."}`) |

## Checkpoint Resumption in ONLINE Mode

The `resume_from_checkpoint` parameter works in ONLINE mode, but with a caveat: on resume, the data preparation steps (response regeneration, preprocessing) **will still re-run**. Only the training step is skipped if already completed.

This means:

- If the job was interrupted **during extraction**, the extraction re-runs from the beginning
- If the job was interrupted **during training**, training resumes from the last checkpoint
- If the job **completed all epochs**, setting `resume_from_checkpoint=True` prevents redundant training

For scenarios where you need to resume from interrupted extraction, consider using [DATA_ONLY](../data-only/) + [TRAIN_ONLY](../train-only/) instead — DATA_ONLY persists hidden states to the PVC, so extraction work is not lost on failure.

## Running the Example

Open `speculator-online-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK and required packages
2. **Configuring authentication and paths** -- API access, PVC mount paths, and model configuration
3. **Configuring the ONLINE trainer** -- Set up extraction and training parameters
4. **Submitting the TrainJob** -- Launch the end-to-end job on the cluster
5. **Monitoring progress** -- Check job status and view logs
6. **Cleanup** -- Delete the TrainJob when complete

## Full Parameter Reference

### SpeculativeDecodingTrainer Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `mode` | `SpeculatorMode.ONLINE` | Must be set to `ONLINE` for this mode |
| `speculator_type` | `SpeculatorType.EAGLE3` | Draft model architecture (currently only Eagle3 is supported) |
| `verifier_model` | String | HuggingFace model ID or PVC URI of the verifier model |
| `dataset_name` | String | Built-in name (`ultrachat`, `magpie`, `gsm8k`) or PVC URI to a `.json`/`.jsonl` file |
| `max_samples` | Integer | Maximum number of dataset samples to process |
| `total_seq_len` | Integer | Maximum sequence length |
| `vllm_resources` | Dict | GPU/CPU/memory for the managed vLLM sidecar (sidecar limited to **1 GPU**) |
| `vllm_gpu_memory_utilization` | Float | GPU memory fraction for vLLM sidecar (0.0–1.0, default: 0.9) |
| `training_resources` | Dict | GPU/CPU/memory for the training container |
| `epochs` | Integer | Number of full passes over the training data |
| `lr` | Float | AdamW learning rate |
| `output_dir` | PVC URI | Directory for checkpoints and final draft model |
| `regenerate_responses` | Boolean | Generate fresh on-policy responses from prompts |
| `vllm_readiness_timeout_minutes` | Integer | vLLM sidecar startup timeout (default: 60, minimum: 1) |
| `enable_progression_tracking` | Boolean | Enable SDK-side progress polling |
| `packages_to_install` | List[str] | Additional Python packages to install |
| `env` | Dict | Environment variables passed to training pods |

### Not Used in ONLINE

The following parameters are not applicable to ONLINE mode:

| Parameter | Why |
| --- | --- |
| `vllm_endpoint` | Not allowed — ONLINE uses a managed sidecar, not an external endpoint |
| `hidden_states_path` | Hidden states are streamed, not persisted to disk |
| `data_path` | Only used in TRAIN_ONLY |

## Customization

| Parameter | Default | Description |
| --- | --- | --- |
| `dataset_name` | `magpie` | Built-in dataset name, HuggingFace ID, or PVC URI |
| `max_samples` | 500 | Maximum number of dataset samples to process |
| `epochs` | 3 | Number of full passes over the training data |
| `lr` | 1e-4 | AdamW learning rate |
| `total_seq_len` | 2048 | Maximum sequence length |
| `vllm_gpu_memory_utilization` | 0.9 | GPU memory fraction for vLLM sidecar |
| `PVC_NAME` | `shared` | Update if you use a different PVC name |

## Troubleshooting

### vLLM sidecar fails to start

If the vLLM sidecar pod fails or gets OOMKilled:

```bash
oc logs <pod-name> -c vllm-sidecar
```

Common fixes:

- Increase `memory` in `vllm_resources` (96Gi is recommended for Qwen3-0.6B)
- Ensure the GPU type supports the model size (Ampere-based or newer recommended)
- Verify the HuggingFace model ID is correct and accessible with your token
- The vLLM sidecar supports only **1 GPU** — if you specified more, you will get a `ValueError`

### vLLM sidecar timeout

If the job fails because the sidecar did not become ready:

- Increase `vllm_readiness_timeout_minutes` (default: 60 minutes). Larger models take longer to load.
- Check GPU availability — if no GPU is available, the sidecar pod stays pending
- Verify the model fits in the allocated GPU memory

### Out of GPU memory during training

If the training container runs out of GPU memory:

- Reduce `total_seq_len` to lower memory usage
- Ensure training and vLLM containers are scheduled on separate GPUs (minimum 2 GPUs total: 1 training + 1 sidecar)
- Check that `training_resources` GPU count matches expectations
- Consider reducing `max_samples` to limit batch sizes

### CTR not found on cluster

If the notebook reports `WARNING: not found on cluster` for the CTR:

- Contact your cluster administrator to verify the CTR is installed
- ONLINE mode requires `vllm-extract-cuda`
- List available CTRs: `oc get clustertrainingruntimes`
