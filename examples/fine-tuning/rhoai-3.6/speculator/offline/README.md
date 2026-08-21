# Offline Mode (Self-Managed vLLM) with SpeculativeDecodingTrainer

This example demonstrates how to train an Eagle3 draft model using the `OFFLINE` mode of `SpeculativeDecodingTrainer`. This mode connects to an external, self-managed vLLM server to extract hidden states, then trains the draft model -- all within a single job.

This is useful when you already have a vLLM deployment running (e.g., as an OpenShift AI model serving instance) and want to reuse it for hidden state extraction instead of having the SDK deploy a sidecar.

This example uses **Qwen3-0.6B** as the verifier model and the `magpie` built-in dataset.

## When to use OFFLINE

| Mode | Best for | vLLM Required | Complexity |
| --- | --- | --- | --- |
| [DATA_ONLY](../data-only/) | Extract once, experiment many times | Managed sidecar or external | Low |
| [TRAIN_ONLY](../train-only/) | Iterate on hyperparameters without re-extracting | None | Low |
| **OFFLINE (this example)** | Reuse an existing vLLM deployment | External (self-managed) | Moderate |
| [ONLINE](../online/) | Simplest end-to-end path | Managed sidecar | Simplest |

OFFLINE mode is the right choice when you already have a vLLM server running and want a single-job workflow that handles both extraction and training. Unlike ONLINE mode, the SDK does **not** manage the vLLM lifecycle — you deploy, configure, and tear down the vLLM server yourself.

**Trade-offs:**

- **vs. ONLINE:** OFFLINE gives you full control over the vLLM server configuration (quantization, tensor parallelism, custom flags) but requires you to manage the server lifecycle separately.
- **vs. DATA_ONLY + TRAIN_ONLY:** OFFLINE runs both steps in one job (simpler to submit), but you cannot reuse the extracted data for multiple training runs with different hyperparameters without re-running extraction.
- **vs. DATA_ONLY with External vLLM:** DATA_ONLY with External vLLM also uses an external vLLM endpoint, but only extracts hidden states — no training. OFFLINE does both extraction and training in a single job.

## How OFFLINE Works

1. The job connects to your external vLLM endpoint to extract hidden states from the verifier model
2. The dataset is preprocessed and tokenized
3. If `regenerate_responses=True`, fresh on-policy responses are generated from the dataset prompts using the external vLLM server
4. Hidden states are extracted from the target layers and saved to the PVC at `hidden_states_path`
5. Training starts immediately after extraction completes — all within the same job
6. The Eagle3 draft model is trained on the extracted hidden states
7. Checkpoints and the final draft model are saved to `output_dir`

The key difference from ONLINE mode is step 1 — the vLLM server is external, not a managed sidecar. The SDK sends extraction requests to your `vllm_endpoint` URL.

## Hardware Requirements

The table below shows the **minimum** resources needed with Qwen3-0.6B. The notebook defaults to minimum values with recommended settings in comments.

| Component | GPU (min) | GPU (rec.) | CPU (min) | CPU (rec.) | Memory (min) | Memory (rec.) |
| --- | --- | --- | --- | --- | --- | --- |
| Training container | 1 | 2 | 1 core | 4 cores | 32Gi | 64Gi |
| External vLLM server | 1 | 1 | 1 core | 4 cores | 48Gi | 96Gi |

- 1 training GPU works but is slower — 2 GPUs enable data-parallel training
- The external vLLM server is self-managed — its resources are separate from the TrainJob

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/fine-tuning/rhoai-3.6/speculator/offline` and open `speculator-offline-example.ipynb`.

### External vLLM Server

Before running this notebook, you must have a vLLM server running that:

- Serves the **same verifier model** (Qwen3-0.6B) used in training
- Exposes the OpenAI-compatible API (typically at port 8000, path `/v1`)
- Is accessible from the training pods (e.g., via a Kubernetes service URL)
- Is in the **same namespace** and has access to the **same shared PVC** as the TrainJob — hidden states are written to the PVC and both the training job and vLLM server must see the same filesystem

> [!IMPORTANT]
>
> The external vLLM server and the TrainJob **must be in the same namespace** and share the **same PVC**. The extraction process writes hidden state tensors to the PVC, and both the training job and the vLLM server need access to the same storage. If they are in different namespaces or use different PVCs, the extraction step will fail because the hidden states will not be accessible to the training step.

<!-- markdownlint-disable-next-line MD028 -->

> [!NOTE]
>
> When using an external vLLM endpoint, the SDK may require `verifier_model` to be specified as a **PVC URI** (e.g., `pvc://shared/models/Qwen3-0.6B`) rather than a HuggingFace ID, since the external vLLM server already has the model loaded from the shared PVC. In this case, `target_layer_ids` must also be provided explicitly in `SpeculatorConfig`.

### ClusterTrainingRuntime (CTR)

OFFLINE mode uses the `speculator-model-opt-cuda` CTR. This CTR provisions only the training container — no vLLM sidecar is included since you manage the vLLM server externally. This is the same CTR used by TRAIN_ONLY mode and DATA_ONLY with External vLLM.

The CTR must be pre-installed on your cluster. The notebook verifies its existence before job submission.

## Verifier Model

The `verifier_model` parameter specifies the large language model whose hidden states are extracted. It accepts two input types:

| Input Type | Example | `target_layer_ids` |
| --- | --- | --- |
| **HuggingFace ID** | `"Qwen/Qwen3-0.6B"` | Auto-computed as `[2, n//2, n-3, n]` where `n` is the number of hidden layers |
| **PVC URI** | `"pvc://shared/models/Qwen3-0.6B"` | Must be provided explicitly — SDK cannot read model config from PVC |

When using a HuggingFace ID, the training pods download the model automatically during the job. Pass your HuggingFace token via the `env` parameter (`{"HF_TOKEN": HF_TOKEN}`) to authenticate.

Direct filesystem paths (e.g., `/mnt/models/...`) are **not supported** — training runs inside Kubernetes pods where local paths from the user's machine do not exist.

## Dataset

The `dataset_name` parameter specifies which dataset to use for hidden state extraction. It accepts multiple input types:

| Input Type | Example | Description |
| --- | --- | --- |
| **Built-in name** | `"ultrachat"`, `"magpie"`, `"gsm8k"` | Downloaded automatically during extraction |
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

## Key OFFLINE Configuration

The key parameters specific to OFFLINE mode:

```python
offline_trainer = SpeculativeDecodingTrainer(
    mode=SpeculatorMode.OFFLINE,
    speculator_type=SpeculatorType.EAGLE3,
    verifier_model=VERIFIER_MODEL,
    dataset_name="magpie",
    max_samples=MAX_SAMPLES,
    total_seq_len=TOTAL_SEQ_LEN,
    vllm_endpoint=VLLM_ENDPOINT,  # External vLLM server URL
    hidden_states_path=f"{OUTPUT}/hidden_states",
    training_resources=TRAINING_RESOURCES,
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

### vLLM Endpoint Parameter

| Parameter | Type | Description |
| --- | --- | --- |
| `vllm_endpoint` | URL string | URL of your external vLLM server. Must include the `/v1` path for the OpenAI-compatible API. Example: `http://vllm-svc.<namespace>.svc.cluster.local:8000/v1`. This is the Kubernetes service DNS name — replace `<namespace>` with your project namespace. |

The endpoint URL follows the Kubernetes service DNS convention: `http://<service-name>.<namespace>.svc.cluster.local:<port>/v1`. You can find your vLLM service name with `oc get svc -n <namespace>`.

### Resource and Path Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `hidden_states_path` | PVC URI | Where extracted hidden states are saved on the PVC. The training step reads from this path after extraction completes. |
| `training_resources` | Dict | GPU/CPU/memory for the training container. Minimum: `{"nvidia.com/gpu": 1, "cpu": "1", "memory": "32Gi"}`. Recommended: `{"nvidia.com/gpu": 2, "cpu": "4", "memory": "64Gi"}` (2 GPUs enable data-parallel training). |

### Training Hyperparameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `epochs` | `3` | Integer | Number of full passes over the training data |
| `lr` | `1e-4` | Float | AdamW learning rate |
| `total_seq_len` | `2048` | Integer | Maximum sequence length for both extraction and training |
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
| `hidden_states_dtype` | `"bfloat16"` | String | Data type for saved tensors: `"bfloat16"`, `"float16"`, or `"float32"` |
| `resume_from_checkpoint` | `False` | Boolean | Resume training from the last saved checkpoint. Restores model weights, optimizer state, and epoch count. |

### Additional Trainer Parameters

These parameters are set directly on `SpeculativeDecodingTrainer(...)`, not inside `SpeculatorConfig`:

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `regenerate_responses` | `False` | Boolean | Generate fresh on-policy responses from prompts before extraction |
| `enable_progression_tracking` | `True` | Boolean | Enable SDK-side progress polling |
| `packages_to_install` | — | List[str] | Additional Python packages to install in the training pod |
| `env` | — | Dict | Environment variables passed to training pods (e.g., `{"HF_TOKEN": "..."}`) |

**Key differences from other modes:**

- You **must** provide `vllm_endpoint` pointing to your external vLLM server
- The SDK does **not** deploy a vLLM sidecar — `vllm_resources` is not used
- Both extraction and training happen in a single job (extract first, then train)
- Both `training_resources` (for the training container) and `vllm_endpoint` (for extraction) are required

## Checkpoint Resumption

The `resume_from_checkpoint` parameter is useful in OFFLINE mode for:

- **Recovering from failures:** If the training step fails after extraction completes, `resume_from_checkpoint=True` prevents re-extracting hidden states on the next submission
- **Extending training:** Increase `epochs` and resubmit with `resume_from_checkpoint=True` to continue from the last checkpoint
- **Pod restarts:** If a training pod is preempted, the trainer picks up from the last saved checkpoint

Note: In OFFLINE mode, if the extraction step completed but training failed, the hidden states remain on the PVC at `hidden_states_path`. On resubmission, the extraction step may re-run (it does not checkpoint independently), but `resume_from_checkpoint=True` ensures training continues from where it left off.

## Running the Example

Open `speculator-offline-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK and required packages
2. **Configuring authentication and paths** -- API access, PVC mount paths, and model configuration
3. **Setting the vLLM endpoint** -- Point to your external vLLM server
4. **Configuring the OFFLINE trainer** -- Set up extraction and training parameters
5. **Submitting the TrainJob** -- Launch the job on the cluster
6. **Monitoring progress** -- Check job status and view logs
7. **Cleanup** -- Delete the TrainJob when complete

## Full Parameter Reference

### SpeculativeDecodingTrainer Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `mode` | `SpeculatorMode.OFFLINE` | Must be set to `OFFLINE` for this mode |
| `speculator_type` | `SpeculatorType.EAGLE3` | Draft model architecture (currently only Eagle3 is supported) |
| `verifier_model` | String | HuggingFace model ID or PVC URI of the verifier model |
| `dataset_name` | String | Built-in name (`ultrachat`, `magpie`, `gsm8k`) or PVC URI to a `.json`/`.jsonl` file |
| `max_samples` | Integer | Maximum number of dataset samples to process |
| `total_seq_len` | Integer | Maximum sequence length |
| `vllm_endpoint` | URL string | External vLLM server URL (required for OFFLINE) |
| `hidden_states_path` | PVC URI | Where extracted hidden states are saved and read for training |
| `training_resources` | Dict | GPU/CPU/memory for the training container |
| `epochs` | Integer | Number of full passes over the training data |
| `lr` | Float | AdamW learning rate |
| `output_dir` | PVC URI | Directory for checkpoints and final draft model |
| `regenerate_responses` | Boolean | Generate fresh on-policy responses from prompts |
| `enable_progression_tracking` | Boolean | Enable SDK-side progress polling |
| `packages_to_install` | List[str] | Additional Python packages to install in the training pod |
| `env` | Dict | Environment variables passed to training pods (e.g., `{"HF_TOKEN": "..."}`) |

### Not Used in OFFLINE

The following parameters are not applicable to OFFLINE mode:

| Parameter | Why |
| --- | --- |
| `vllm_resources` | No managed vLLM sidecar — the external server handles extraction |
| `vllm_gpu_memory_utilization` | No managed vLLM sidecar |
| `data_path` | Only used in TRAIN_ONLY |

## Customization

| Parameter | Default | Description |
| --- | --- | --- |
| `VLLM_ENDPOINT` | `http://vllm-svc.<namespace>.svc.cluster.local:8000/v1` | URL of your external vLLM server |
| `dataset_name` | `magpie` | Built-in dataset name, HuggingFace ID, or PVC URI |
| `max_samples` | 500 | Maximum number of dataset samples to process |
| `epochs` | 3 | Number of full passes over the training data |
| `lr` | 1e-4 | AdamW learning rate |
| `total_seq_len` | 2048 | Maximum sequence length |
| `PVC_NAME` | `shared` | Update if you use a different PVC name |

## Troubleshooting

### Cannot connect to vLLM endpoint

If the job fails with a connection error:

```bash
oc logs <pod-name> -c node | grep -i "connection"
```

Common fixes:

- Verify the vLLM service is running: `oc get svc -n <namespace>`
- Check the endpoint URL format (must include `/v1`)
- Ensure the vLLM server is in the **same namespace** as the TrainJob
- Ensure the vLLM server has access to the **same shared PVC**
- Ensure network policies allow traffic from the training pod to the vLLM service
- Verify the vLLM server is serving the correct model

### Extraction succeeds but training fails

If hidden states are extracted but training errors occur:

- Check GPU memory -- the training container needs its own GPU allocation
- Verify `target_layer_ids` match the model served by the vLLM endpoint
- Review training logs for OOM or configuration errors
- If the training container runs out of memory, reduce `total_seq_len` or increase `memory` in `training_resources`

### Hidden states path issues

If the training step cannot find the extracted hidden states:

- Verify `hidden_states_path` points to a valid location on the shared PVC
- Ensure both the vLLM server and the training pod mount the same PVC
- Check that the extraction step completed before training started (review job logs)

### CTR not found on cluster

If the notebook reports `WARNING: not found on cluster` for the CTR:

- Contact your cluster administrator to verify the CTR is installed
- OFFLINE mode requires `speculator-model-opt-cuda`
- List available CTRs: `oc get clustertrainingruntimes`
