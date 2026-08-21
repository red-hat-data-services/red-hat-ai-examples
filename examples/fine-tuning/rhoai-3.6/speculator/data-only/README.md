# Data Extraction (DATA_ONLY) with SpeculativeDecodingTrainer

This example demonstrates how to extract hidden states from a verifier model using the `DATA_ONLY` mode of `SpeculativeDecodingTrainer`. DATA_ONLY supports two extraction methods:

- **Method 1 — Managed vLLM Sidecar:** The SDK deploys a managed vLLM sidecar alongside the job pod to serve the verifier model. Simplest option — no external infrastructure needed.
- **Method 2 — External vLLM Endpoint:** You provide a running vLLM server. The SDK connects to it for extraction without deploying a sidecar. Useful when you already have a vLLM deployment (e.g., an OpenShift AI model serving instance).

Both methods produce identical output — hidden state tensors (`.safetensors` files) written to the output PVC. No training happens in this mode. It is the first step of a two-step workflow: extract hidden states once, then train the draft model many times with different hyperparameters using [TRAIN_ONLY](../train-only/).

This example uses **Qwen3-0.6B** as the verifier model and the `ultrachat` built-in dataset.

## When to use DATA_ONLY

| Mode | Best for | vLLM Required | Complexity |
| --- | --- | --- | --- |
| **DATA_ONLY (this example)** | Extract once, experiment many times | Managed sidecar or external | Low |
| [TRAIN_ONLY](../train-only/) | Iterate on hyperparameters without re-extracting | None | Low |
| [OFFLINE](../offline/) | Reuse an existing vLLM deployment | External (self-managed) | Moderate |
| [ONLINE](../online/) | Simplest end-to-end path | Managed sidecar | Simplest |

DATA_ONLY is the recommended first step when you plan to experiment with training hyperparameters. Hidden state extraction is the most expensive operation — it requires loading the full verifier model into GPU memory and processing every dataset sample through a forward pass. By extracting once and saving the results to the PVC, you can run dozens of TRAIN_ONLY experiments (varying learning rate, epochs, sequence length, etc.) without repeating the extraction cost.

**Trade-off:** DATA_ONLY + TRAIN_ONLY requires two separate jobs and more disk space (hidden states are persisted), but saves significant GPU time when iterating. If you only need a single training run, consider [ONLINE](../online/) or [OFFLINE](../offline/) mode instead.

## How DATA_ONLY Works

1. The verifier model (e.g., Qwen3-0.6B) is loaded into the vLLM server — either a managed sidecar (Method 1) or your external deployment (Method 2)
2. The dataset is preprocessed and tokenized
3. If `regenerate_responses=True`, fresh on-policy responses are generated from the dataset prompts using the vLLM server, replacing the original dataset responses
4. Each sample is fed through the verifier model, and hidden states are captured from the 4 target layers specified by `target_layer_ids`
5. Hidden states are saved as `.safetensors` files to `hidden_states_path` on the PVC
6. The job completes — no training is performed

The output directory will contain:

- `hidden_states/` — Extracted hidden state tensors (`.safetensors` format)
- Preprocessed dataset files used during extraction
- If `regenerate_responses=True`, a `regenerated_responses.jsonl` file with the model-generated responses

## Setup

See the [common setup guide](../README.md#setup) for step-by-step instructions on creating a workbench, shared storage, and cloning the repository.

Navigate to `examples/fine-tuning/rhoai-3.6/speculator/data-only` and open `speculator-data-only-example.ipynb`.

## Extraction Methods

### Method 1: Managed vLLM Sidecar

The SDK deploys a vLLM sidecar container alongside the extraction job pod. The sidecar serves the verifier model, processes the dataset, and is automatically cleaned up when the job completes. This is the simplest approach — no external infrastructure is required.

**ClusterTrainingRuntime (CTR):** `vllm-extract-cuda`

This CTR is specifically designed for data extraction with a managed vLLM sidecar. It provisions a pod with the vLLM container alongside the extraction worker. The CTR must be pre-installed on your cluster — verify it exists before submitting the job.

```python
data_only_sidecar = SpeculativeDecodingTrainer(
    mode=SpeculatorMode.DATA_ONLY,
    speculator_type=SpeculatorType.EAGLE3,
    verifier_model=VERIFIER_MODEL,  # HuggingFace ID or PVC URI
    dataset_name="ultrachat",  # Built-in, HuggingFace ID, or PVC URI
    max_samples=MAX_SAMPLES,
    total_seq_len=TOTAL_SEQ_LEN,
    vllm_resources=VLLM_RESOURCES,  # GPU/CPU/memory for the sidecar
    vllm_gpu_memory_utilization=0.9,  # 90% GPU memory for vLLM
    hidden_states_path=f"{OUTPUT}/hidden_states",
    regenerate_responses=True,
    output_dir=OUTPUT,
    config=SpeculatorConfig(
        target_layer_ids=TARGET_LAYER_IDS,
        datagen_concurrency=4,
        hidden_states_dtype="bfloat16",
    ),
    env={"HF_TOKEN": HF_TOKEN},
    # ...
)
```

#### Method 1 Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `vllm_resources` | Dict | GPU/CPU/memory for the managed vLLM sidecar. The sidecar currently supports only **1 GPU** — providing more raises a `ValueError`. Example: `{"nvidia.com/gpu": 1, "cpu": "4", "memory": "96Gi"}` |
| `vllm_gpu_memory_utilization` | Float (0.0–1.0) | Fraction of GPU memory the vLLM sidecar can use. Default is 0.9 (90%). Lower this if you encounter OOM errors during model loading. |
| `regenerate_responses` | Boolean | When `True`, generates new on-policy responses from dataset prompts before extracting hidden states. The regenerated responses are saved as a `.jsonl` file and used instead of the original dataset answers. Default: `False`. |
| `datagen_concurrency` | Integer | Number of concurrent data generation workers. Higher values speed up extraction but increase memory usage. Set via `SpeculatorConfig`. |
| `hidden_states_dtype` | String | Data type for saved tensors. `"bfloat16"` halves disk usage compared to `"float32"` with negligible quality impact. Set via `SpeculatorConfig`. |

### Method 2: External vLLM Endpoint

You provide a running vLLM server. The SDK connects to it via `vllm_endpoint` for hidden state extraction — no sidecar is deployed. This method is useful when:

- You already have a vLLM deployment running (e.g., an OpenShift AI model serving instance)
- You need custom vLLM configuration (quantization, tensor parallelism, etc.)
- You want to share a single vLLM server across multiple extraction jobs

**ClusterTrainingRuntime (CTR):** `speculator-model-opt-cuda`

This CTR provisions only the extraction worker — no vLLM sidecar. It is the same CTR used by TRAIN_ONLY and OFFLINE modes. Since vLLM is external, fewer resources are needed in the pod.

```python
data_only_external = SpeculativeDecodingTrainer(
    mode=SpeculatorMode.DATA_ONLY,
    speculator_type=SpeculatorType.EAGLE3,
    verifier_model=VERIFIER_MODEL,
    dataset_name="ultrachat",
    max_samples=MAX_SAMPLES,
    total_seq_len=TOTAL_SEQ_LEN,
    vllm_endpoint=VLLM_ENDPOINT,  # External vLLM server URL
    hidden_states_path=f"{OUTPUT}/hidden_states",
    regenerate_responses=True,
    output_dir=OUTPUT,
    config=SpeculatorConfig(
        target_layer_ids=TARGET_LAYER_IDS,
        datagen_concurrency=4,
        hidden_states_dtype="bfloat16",
    ),
    env={"HF_TOKEN": HF_TOKEN},
    # ...
)
```

#### Method 2 Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `vllm_endpoint` | URL string | URL of your external vLLM server. Must include the `/v1` path for the OpenAI-compatible API. Example: `http://vllm-svc.<namespace>.svc.cluster.local:8000/v1` |

#### Prerequisites for Method 2

Before running this method, you must have a vLLM server running that:

- Serves the **same verifier model** (Qwen3-0.6B) used in the extraction configuration
- Exposes the OpenAI-compatible API (typically at port 8000, path `/v1`)
- Is accessible from the extraction pods (e.g., via a Kubernetes service URL)
- Is in the **same namespace** and has access to the **same shared PVC** as the TrainJob — hidden states are written to the PVC and both the extraction job and vLLM server must see the same filesystem

> [!IMPORTANT]
>
> The external vLLM server and the TrainJob **must be in the same namespace** and share the **same PVC**. The extraction process writes hidden state tensors to the PVC, and both the extraction job and the vLLM server need access to the same storage. If they are in different namespaces or use different PVCs, the job will fail because the hidden states will not be accessible.

<!-- markdownlint-disable-next-line MD028 -->

> [!NOTE]
>
> When using an external vLLM endpoint, the SDK may require `verifier_model` to be specified as a **PVC URI** (e.g., `pvc://shared/models/Qwen3-0.6B`) rather than a HuggingFace ID, since the external vLLM server already has the model loaded from the shared PVC. In this case, `target_layer_ids` and `hidden_states_path` must also be provided explicitly.

## Verifier Model

The `verifier_model` parameter specifies the large language model whose hidden states are extracted. It accepts two input types:

| Input Type | Example | `target_layer_ids` |
| --- | --- | --- |
| **HuggingFace ID** | `"Qwen/Qwen3-0.6B"` | Auto-computed as `[2, n//2, n-3, n]` where `n` is the number of hidden layers |
| **PVC URI** | `"pvc://shared/models/Qwen3-0.6B"` | Must be provided explicitly — SDK cannot read model config from PVC |

When using a HuggingFace ID, the training pods download the model automatically during the job. Pass your HuggingFace token via the `env` parameter (`{"HF_TOKEN": HF_TOKEN}`) to authenticate, especially for gated models. Even for non-gated models like Qwen3-0.6B, a token is recommended to avoid rate limits.

Direct filesystem paths (e.g., `/mnt/models/...`) are **not supported** — training runs inside Kubernetes pods where local paths from the user's machine do not exist.

## Dataset

The `dataset_name` parameter specifies which dataset to use for hidden state extraction. It accepts multiple input types:

| Input Type | Example | Description |
| --- | --- | --- |
| **Built-in name** | `"ultrachat"`, `"magpie"`, `"gsm8k"` | Downloaded automatically during extraction |
| **PVC URI** | `"pvc://shared/datasets/custom.jsonl"` | Self-provided JSON/JSONL file on the PVC — requires `regenerate_responses=False` |

The `max_samples` parameter caps how many samples are processed. The `total_seq_len` parameter sets the maximum sequence length for tokenization — longer sequences capture more context but require more GPU memory and disk space for the hidden states.

## Target Layer IDs

Eagle3 reads hidden states from exactly **4 intermediate layers** of the verifier model. These layers are chosen to give the draft model a spread of representations:

- **Early layer** — captures low-level token features
- **Middle layer** — captures mid-level semantic patterns
- **Late layer** — captures high-level reasoning
- **Final layer** — provides the target distribution for training

For Qwen3-0.6B (28 hidden layers), the auto-computed formula `[2, n//2, n-3, n]` gives `[2, 14, 25, 28]`.

When using a PVC URI for `verifier_model`, you **must** provide `target_layer_ids` explicitly via `SpeculatorConfig(target_layer_ids=[...])` because the SDK cannot access the model configuration file from the PVC at validation time. The SDK validates that exactly 4 IDs are provided — fewer or more raises a `ValueError`.

## Hardware Requirements

The table below shows the **minimum** resources needed to run each method with Qwen3-0.6B.
The notebooks default to minimum values with recommended settings in comments.

| Method | Component | GPU (min) | GPU (rec.) | CPU (min) | CPU (rec.) | Memory (min) | Memory (rec.) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Method 1 (sidecar) | vLLM sidecar | 1 | 1 | 1 core | 4 cores | 48Gi | 96Gi |
| Method 2 (external) | Extraction pod | 0 | 0 | 1 core | 2 cores | 16Gi | 32Gi |

- The vLLM sidecar is hard-limited to exactly **1 GPU** — more raises a `ValueError`
- Method 2 needs no GPU in the TrainJob pod since vLLM runs externally
- No training container is deployed in DATA_ONLY mode

## Output Structure

After a successful DATA_ONLY run, the output directory on the PVC will contain:

```text
pvc://shared/speculator/run-01-data/
├── hidden_states/          # Extracted hidden state tensors (.safetensors)
├── preprocessed data       # Tokenized and formatted dataset
└── regenerated_responses.jsonl  # (only if regenerate_responses=True)
```

The `hidden_states/` directory is the input for a subsequent [TRAIN_ONLY](../train-only/) run. Point the TRAIN_ONLY trainer's `hidden_states_path` to this directory.

## Running the Example

Open `speculator-data-only-example.ipynb` and follow the notebook, which walks you through:

1. **Installing dependencies** -- Kubeflow SDK and required packages
2. **Configuring authentication and paths** -- API access, PVC mount paths, CTRs for both methods
3. **Configuring shared parameters** -- Model, target layers, output paths, and method-specific settings
4. **Method 1: Managed vLLM Sidecar** -- Configure, submit, and monitor the extraction job with a managed sidecar
5. **Method 2: External vLLM Endpoint** -- Configure, submit, and monitor the extraction job with an external vLLM server
6. **Cleanup** -- Delete the TrainJob when extraction is complete

Run the cells for **one or both methods** depending on your setup. Both methods produce identical hidden state output — the only difference is how the vLLM server is provisioned.

## Full Parameter Reference

### SpeculativeDecodingTrainer Parameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `mode` | — | `SpeculatorMode.DATA_ONLY` | Must be set to `DATA_ONLY` for this mode |
| `speculator_type` | — | `SpeculatorType.EAGLE3` | Draft model architecture (currently only Eagle3 is supported) |
| `verifier_model` | — | String | HuggingFace model ID or PVC URI of the verifier model |
| `dataset_name` | — | String | Built-in name (`ultrachat`, `magpie`, `gsm8k`) or PVC URI to a `.json`/`.jsonl` file |
| `max_samples` | — | Integer | Maximum number of dataset samples to process |
| `total_seq_len` | — | Integer | Maximum sequence length for tokenization |
| `output_dir` | — | PVC URI | Directory where output files are saved |
| `hidden_states_path` | — | PVC URI | Where extracted hidden state tensors are written |
| `vllm_resources` | — | Dict | GPU/CPU/memory for the managed vLLM sidecar (Method 1 only). Sidecar limited to **1 GPU**. |
| `vllm_gpu_memory_utilization` | `0.9` | Float | Fraction of GPU memory for the vLLM sidecar (Method 1 only) |
| `vllm_endpoint` | — | URL string | External vLLM server URL (Method 2 only) |
| `regenerate_responses` | `False` | Boolean | Generate fresh on-policy responses from prompts before extraction |
| `enable_progression_tracking` | — | Boolean | Enable SDK-side progress polling |
| `packages_to_install` | — | List[str] | Additional Python packages to install in the training pod |
| `env` | — | Dict | Environment variables passed to training pods (e.g., `{"HF_TOKEN": "..."}`) |

### SpeculatorConfig Parameters

| Parameter | Default | Type | Description |
| --- | --- | --- | --- |
| `target_layer_ids` | Auto-computed | List[int] | 4 transformer layer IDs for hidden state extraction. Auto-detected from HuggingFace model config; must be explicit for PVC URI models. |
| `datagen_concurrency` | — | Integer | Number of parallel data generation workers |
| `hidden_states_dtype` | — | String | Data type for saved tensors (`"bfloat16"` or `"float32"`) |

## Troubleshooting

### Method 1: vLLM sidecar fails to start

If the vLLM sidecar pod fails or gets OOMKilled:

```bash
oc logs <pod-name> -c vllm-sidecar
```

Common fixes:

- Increase `memory` in `vllm_resources` (96Gi is recommended for Qwen3-0.6B)
- Ensure the GPU type supports the model size (Ampere-based or newer recommended)
- Verify the HuggingFace model ID is correct and accessible with your token
- The vLLM sidecar supports only **1 GPU** — if you specified more, you will get a `ValueError`

### Method 2: Cannot connect to vLLM endpoint

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

### Hidden states output is empty

If no `.safetensors` files appear in the output directory:

- Verify `target_layer_ids` match the verifier model architecture (exactly 4 IDs required)
- Check that `dataset_name` is valid and accessible:
  - Built-in names: `ultrachat`, `magpie`, `gsm8k`
  - PVC URIs must end with `.json` or `.jsonl`
- Ensure vLLM endpoint became ready (check `vllm_readiness_timeout_minutes` if model is large)
- Verify preprocessing completed successfully (check logs for "Preprocessing dataset" messages)
- If `regenerate_responses=True`, ensure you are using a built-in dataset (not a PVC URI)
- Check that the incomplete marker file (`.extraction_incomplete.rank-*`) was removed after completion

### CTR not found on cluster

If the notebook reports `WARNING: not found on cluster` for a CTR:

- Contact your cluster administrator to verify the CTR is installed
- Method 1 requires `vllm-extract-cuda`, Method 2 requires `speculator-model-opt-cuda`
- List available CTRs: `oc get clustertrainingruntimes`
