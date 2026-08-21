# Speculative Decoding Draft Model Training via Kubeflow Trainer

This example demonstrates how to train a custom Eagle3 draft model for speculative decoding using the `SpeculativeDecodingTrainer` from the Kubeflow SDK on Red Hat OpenShift AI.

## What is Speculative Decoding?

Large language models generate tokens one at a time during inference. Each token requires reading the entire model from GPU memory (e.g., 140 GB for a 70B model in FP16), but the actual computation for one token is tiny. The GPU spends most of its time waiting for data to arrive from memory — running at under 1% compute utilization during normal token generation. This is called being **memory-bound**.

Speculative decoding exploits a key insight: verifying multiple tokens at once costs almost the same as generating one, because the expensive part (reading the model from memory) is identical and the GPU's compute units are idle anyway. A small, fast **draft model** (~1.2 GB with Qwen3-0.6B) quickly guesses the next several tokens, then the large **verifier model** checks all guesses at once in a single forward pass. Correct guesses become output; at the first rejected guess, the verifier's own token is used and the draft model starts guessing again. The output is mathematically identical to normal decoding — no quality loss.

### Why Custom Draft Models?

vLLM already supports Eagle3 speculative decoding at serving time — if you have a draft model, you can deploy it today. Pre-built draft models (like those on HuggingFace) only work well with the original base model. After fine-tuning, the model's internal behavior changes, so a pre-built draft model's guesses no longer match and the acceptance rate drops significantly. Customers need a **custom draft model** trained specifically for their fine-tuned model to achieve meaningful inference speedup.

### Eagle3 Architecture

[Eagle3](https://arxiv.org/abs/2503.01840) is a draft model architecture that reads hidden states from four intermediate layers of the verifier model (not just the final logits), giving it richer context for more accurate predictions. The draft model is very small (~1.2 GB with Qwen3-0.6B) and consists of just two fully-connected layers and one Transformer decoder layer. The verifier model is never modified — only the draft model is trained.

## Training Modes

`SpeculativeDecodingTrainer` supports four training modes:

| Mode | Description | Use Case | Example |
| --- | --- | --- | --- |
| `DATA_ONLY` | Extracts hidden states from the verifier model. Supports a managed vLLM sidecar or an external vLLM endpoint. No training. | First step of a two-step workflow. Extract once, experiment with training hyperparameters many times. | [data-only/](data-only/) |
| `TRAIN_ONLY` | Trains the draft model from pre-extracted hidden states. No vLLM needed. | Second step after `DATA_ONLY`. Iterate on hyperparameters without re-running extraction. | [train-only/](train-only/) |
| `OFFLINE` | Extracts hidden states via a self-managed external vLLM server, then trains. | When you already have a vLLM deployment or need custom vLLM configuration. | [offline/](offline/) |
| `ONLINE` | Fully managed end-to-end: SDK deploys a vLLM sidecar, extracts hidden states, and trains. | Simplest path — recommended when you want everything in one step. | [online/](online/) |

Each mode has its own subfolder with a dedicated notebook and README.

## Supported Datasets

The SDK provides three built-in dataset names that can be used directly with the `dataset_name` parameter:

| Name | Description |
| --- | --- |
| `ultrachat` | Multi-turn conversational dataset |
| `magpie` | Magpie-format conversation dataset |
| `gsm8k` | Grade school math word problems |

You can also pass a PVC URI (`pvc://<pvc-name>/<path>`) pointing to a `.json`/`.jsonl` file as `dataset_name`.

> [!NOTE]
>
> `regenerate_responses=True` only supports these three built-in datasets. Custom datasets via PVC URIs or HuggingFace IDs require `regenerate_responses=False`.

## RHOAI compatibility

This example is compatible with RHOAI version 3.6EA1.

## Requirements

- An OpenShift cluster with OpenShift AI (RHOAI 3.6EA1) installed:
  - The `dashboard` and `workbenches` components enabled
  - The `trainer` component enabled
  - ClusterTrainingRuntimes (CTRs) deployed for speculator training — different modes require different CTRs (data extraction, model optimization, online)
- Sufficient worker nodes with **NVIDIA GPUs** — the CTRs are CUDA-based, so only NVIDIA GPUs are supported. Ampere-based or newer recommended.
- A dynamic storage provisioner supporting RWX PVC provisioning. Talk to your cluster administrator about RWX storage options.
- A HuggingFace account and token (for downloading models and avoiding rate limits).

## Hardware requirements

The hardware requirements below are specific to these examples using **Qwen3-0.6B** as the verifier model. Requirements scale with verifier model size — larger models need more GPU memory and storage.

For the workbench image, the example was run on `Training | Jupyter | PyTorch | CUDA | Python`.
The workbench only submits TrainJobs and monitors progress — no GPU is required on the workbench itself.

### Workbench Requirements

| Image Type | Use Case | GPU | CPU | Memory | Notes |
| --- | --- | --- | --- | --- | --- |
| Training \| Jupyter \| PyTorch \| CUDA \| Python | Job submission and monitoring | None | 2 cores | 8Gi | No GPU needed; the workbench only submits TrainJobs |

> [!NOTE]
>
> - The workbench does not perform training or inference. All compute-intensive work happens in the TrainJob pods.

### Training Pod Requirements

The table below shows the **minimum** and **recommended** resources for each component with Qwen3-0.6B. The example notebooks default to minimum values with recommended settings in comments.

| Component | GPU (min) | GPU (rec.) | CPU (min) | CPU (rec.) | Memory (min) | Memory (rec.) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Training container | 1 | 2 | 1 core | 4 cores | 32Gi | 64Gi | Runs Eagle3 draft model training |
| vLLM sidecar | 1 | 1 | 1 core | 4 cores | 48Gi | 96Gi | Runs verifier model for hidden state extraction |

Which components are deployed depends on the training mode:

| Mode | Training Container | vLLM Sidecar | TrainJob GPUs (min) |
| --- | --- | --- | --- |
| `DATA_ONLY` with Managed Sidecar | No | Yes | 1 |
| `DATA_ONLY` with External vLLM | No | No (external) | 0 |
| `TRAIN_ONLY` | Yes | No | 1 |
| `OFFLINE` | Yes | No (external) | 1 |
| `ONLINE` | Yes | Yes | 2 |

> [!NOTE]
>
> - These values are for the Qwen3-0.6B examples. CPU, memory, and GPU requirements scale with verifier model size.
> - 1 training GPU works but is slower — 2 GPUs enable data-parallel training.
> - `OFFLINE` mode uses an external vLLM server instead of a sidecar — configure its resources separately.
> - The vLLM sidecar currently supports only 1 GPU.

### Storage Requirements

| Purpose | Size | Access Mode | Storage Class | Notes |
| --- | --- | --- | --- | --- |
| Shared Storage (PVC) total | 100Gi (Example Default) | RWX | Dynamic provisioner required | Shared between workbench and training pods |

> [!NOTE]
>
> - The PVC stores downloaded models, extracted hidden states, and trained draft model checkpoints.
> - Storage can be created in `Create Workbench` view on RHOAI Platform, however, dynamic RWX provisioner is required to be configured prior to creating shared file storage in RHOAI.
> - 100Gi is recommended to accommodate the verifier model weights, hidden state data, and output checkpoints.

## Speculator-specific considerations

- **PVC URIs**: All storage paths use PVC URIs (`pvc://<pvc-name>/<path>`). The SDK resolves these to container mount paths internally — do not use direct filesystem paths.
- **Model download**: The verifier model can be specified as a HuggingFace model ID (e.g., `Qwen/Qwen3-0.6B`) or a PVC URI pointing to a pre-downloaded model (e.g., `pvc://shared/models/Qwen3-0.6B`). When using a HuggingFace ID, the training pods download the model automatically — pass your HuggingFace token via the `env` parameter to authenticate.
- **Target layer IDs**: When using a HuggingFace model ID, the SDK auto-detects `target_layer_ids`. When using a PVC URI, you must provide them explicitly via `SpeculatorConfig` because the SDK cannot access the model config from the PVC. The example notebooks set them explicitly for clarity.
- **ClusterTrainingRuntimes**: Different training modes use different ClusterTrainingRuntimes (CTRs). Each mode requires a specific CTR:
  - `DATA_ONLY` with Managed Sidecar / `ONLINE` — `vllm-extract-cuda` (data extraction CTR that includes a managed vLLM sidecar; ONLINE reuses the same CTR — there is no specific sidecar requirement for ONLINE)
  - `DATA_ONLY` with External vLLM / `TRAIN_ONLY` / `OFFLINE` — `speculator-model-opt-cuda` (training only, no vLLM sidecar)
  
  These CTRs must be pre-installed on your cluster by an admin. Each notebook verifies their existence before job submission.
- **External vLLM requirements**: When using an external vLLM endpoint (`DATA_ONLY` with External vLLM or `OFFLINE` mode), the vLLM server must be in the **same namespace** and have access to the **same shared PVC** as the TrainJob.
- **HuggingFace token**: Passed to training pods via the `env` parameter on each trainer. Required for downloading gated models. Qwen3-0.6B is not gated, but a token avoids rate limits.
- **Job naming**: Use `options=[Name(name="...")]` to give jobs explicit, predictable names. This makes it easier to monitor logs with `oc logs` and check job status with `trainer_client.get_job()`.
- **No manual PVC mounts**: `SpeculativeDecodingTrainer` handles PVC mounting internally via PVC URIs. You do not need to configure volume mounts manually.

## Parameter Reference

The example notebooks demonstrate common configurations for each training mode. The `SpeculativeDecodingTrainer` SDK supports additional parameters beyond what the notebooks cover. This section provides a complete reference so you can customize your training runs.

> [!NOTE]
>
> All path-based parameters accept only **PVC URIs** (`pvc://<pvc-name>/<path>`) or **HuggingFace IDs** — direct filesystem paths like `/data/models/...` are not supported because training runs inside Kubernetes pods where local paths from the user's machine do not exist.

### Core Parameters

| Parameter | Type | Description | Modes |
| --- | --- | --- | --- |
| `verifier_model` | HuggingFace ID or PVC URI | The base LLM used for hidden state extraction and as the reference model during training. When using a HuggingFace ID, the SDK downloads the model and auto-detects `target_layer_ids`. When using a PVC URI, `target_layer_ids` must be set explicitly. | All |
| `output_dir` | PVC URI | Directory where training checkpoints and the final draft model are saved. | All |
| `dataset_name` | Built-in name or PVC URI | The dataset for data preprocessing and hidden state extraction. Built-in names: `ultrachat`, `magpie`, `gsm8k`. Also accepts PVC URIs pointing to `.json`/`.jsonl` files. | DATA_ONLY, OFFLINE, ONLINE |
| `hidden_states_path` | PVC URI | Directory for hidden state `.safetensors` files. **DATA_ONLY**: output — extracted states are written here. **TRAIN_ONLY**: input — reads states from a prior DATA_ONLY run. **OFFLINE**: output then input — states are extracted and consumed within the same job. When using an external vLLM server, ensure its `hidden_states_path` matches the path configured in the training job. | DATA_ONLY, TRAIN_ONLY, OFFLINE |

### Resource Parameters

| Parameter | Type | Description | Modes |
| --- | --- | --- | --- |
| `training_resources` | Dict | GPU/CPU/memory for the training container. Example: `{"nvidia.com/gpu": 2, "cpu": "4", "memory": "64Gi"}` | TRAIN_ONLY, OFFLINE, ONLINE |
| `vllm_resources` | Dict | GPU/CPU/memory for the managed vLLM sidecar. The vLLM sidecar currently supports only **1 GPU** — providing more raises a `ValueError`. Example: `{"nvidia.com/gpu": 1, "cpu": "4", "memory": "96Gi"}` | DATA_ONLY with Managed Sidecar, ONLINE |
| `vllm_endpoint` | URL string | URL of an external vLLM server for hidden state extraction (e.g., `http://vllm-svc.<namespace>.svc.cluster.local:8000/v1`). When provided in DATA_ONLY mode, the SDK uses the external endpoint instead of the managed sidecar. When using an external endpoint, `verifier_model` may need to be a PVC URI (not a HuggingFace ID). | DATA_ONLY with External vLLM, OFFLINE |

### Training Configuration via SpeculatorConfig

These parameters are set inside `SpeculatorConfig(...)` and control training behavior:

| Parameter | Default | Type | Description | Modes |
| --- | --- | --- | --- | --- |
| `num_layers` | `1` | int | Number of Transformer decoder layers in the draft model. | TRAIN_ONLY, OFFLINE, ONLINE |
| `ttt_steps` | `3` | int | Test-time training steps per batch. | TRAIN_ONLY, OFFLINE, ONLINE |
| `norm_before_residual` | `True` | bool | Apply LayerNorm before the residual connection. | TRAIN_ONLY, OFFLINE, ONLINE |
| `norm_before_fc` | `False` | bool | Apply LayerNorm before the fully-connected layer. | TRAIN_ONLY, OFFLINE, ONLINE |
| `embed_requires_grad` | `False` | bool | Whether the embedding layer requires gradient updates. | TRAIN_ONLY, OFFLINE, ONLINE |
| `hidden_states_dtype` | `"bfloat16"` | str | Data type for saved tensors. Must be `"bfloat16"`, `"float16"`, or `"float32"`. | DATA_ONLY, OFFLINE, ONLINE |
| `scheduler_type` | `"linear"` | str | Learning rate scheduler. Must be `"linear"`, `"cosine"`, or `"none"`. | TRAIN_ONLY, OFFLINE, ONLINE |
| `scheduler_warmup_steps` | `None` | int \| None | Number of warmup steps for the learning rate scheduler. | TRAIN_ONLY, OFFLINE, ONLINE |
| `scheduler_total_steps` | `None` | int \| None | Total number of steps for the scheduler. If `None`, computed from epochs and dataset size. | TRAIN_ONLY, OFFLINE, ONLINE |
| `scheduler_num_cosine_cycles` | `0.5` | float | Number of cosine cycles when using the `"cosine"` scheduler. | TRAIN_ONLY, OFFLINE, ONLINE |
| `checkpoint_freq` | `1.0` | float | Save a checkpoint every N epochs. | TRAIN_ONLY, OFFLINE, ONLINE |
| `save_best` | `False` | bool | Save only the best checkpoint by validation loss. | TRAIN_ONLY, OFFLINE, ONLINE |
| `log_freq` | `1` | int | Logging frequency in training steps. | TRAIN_ONLY, OFFLINE, ONLINE |
| `resume_from_checkpoint` | `False` | bool | Resume training from the last saved checkpoint in `output_dir`. Restores model weights, optimizer state, and epoch count. Important for recovering from pod restarts or re-submissions. | TRAIN_ONLY, OFFLINE, ONLINE |
| `datagen_concurrency` | `4` | int | Number of concurrent vLLM extraction requests. | DATA_ONLY, OFFLINE, ONLINE |
| `target_layer_ids` | `None` | list[int] \| None | 4 transformer layer IDs for hidden state extraction. Auto-detected from HuggingFace model config; must be explicit for PVC URI models. | All |
| `from_pretrained` | `None` | str \| None | Path to a pre-trained draft model to fine-tune instead of training from scratch. | TRAIN_ONLY, OFFLINE, ONLINE |

### Additional Trainer Parameters

These parameters are set directly on `SpeculativeDecodingTrainer(...)`:

| Parameter | Default | Type | Description | Modes |
| --- | --- | --- | --- | --- |
| `epochs` | `3` | int | Number of full passes over the training data. | TRAIN_ONLY, OFFLINE, ONLINE |
| `lr` | `1e-4` | float | AdamW learning rate. | TRAIN_ONLY, OFFLINE, ONLINE |
| `total_seq_len` | `2048` | int | Maximum sequence length for extraction and training. | All |
| `max_samples` | `None` | int \| None | Maximum number of dataset samples to process. `None` uses the full dataset. | DATA_ONLY, OFFLINE, ONLINE |
| `draft_vocab_size` | `None` | int \| None | Vocabulary size override for the draft model. `None` inherits from the verifier. | TRAIN_ONLY, OFFLINE, ONLINE |
| `regenerate_responses` | `False` | bool | Generate fresh on-policy responses from the vLLM endpoint before preprocessing, rather than using static dataset responses. Only supports built-in datasets. | DATA_ONLY, OFFLINE, ONLINE |
| `vllm_readiness_timeout_minutes` | `60` | int | How long to wait for the vLLM server to become ready. Minimum: 1 minute, default: 60 minutes. Increase this for larger models that require more load time. | All |
| `vllm_gpu_memory_utilization` | `0.9` | float | Fraction of GPU memory the vLLM sidecar can use (range: 0.0–1.0). | DATA_ONLY with Managed Sidecar, ONLINE |
| `enable_progression_tracking` | `True` | bool | Enable SDK-side progress polling. | All |
| `metrics_port` | `28080` | int | Port for the metrics server used by progression tracking. | All |
| `metrics_poll_interval_seconds` | `30` | int | Polling interval in seconds for progression tracking. | All |
| `packages_to_install` | `None` | list[str] \| None | Additional Python packages to install in the training pod. | All |
| `pip_index_urls` | SDK defaults | list[str] | PyPI index URLs for package installation. | All |
| `env` | `None` | dict \| None | Environment variables passed to training pods (e.g., `{"HF_TOKEN": "..."}`). | All |

### Mode–Parameter Applicability Matrix

| Parameter | DATA_ONLY | TRAIN_ONLY | OFFLINE | ONLINE |
| --- | --- | --- | --- | --- |
| `verifier_model` | Required | Required | Required | Required |
| `output_dir` | Required | Required | Required | Required |
| `dataset_name` | Required | Not used | Required | Required |
| `hidden_states_path` | Output | Required | Required | Output |
| `target_layer_ids` | Auto or explicit | Auto or explicit | Auto or explicit | Auto or explicit |
| `training_resources` | Not used | Required | Required | Required |
| `vllm_resources` | Required (Managed Sidecar) | Not used | Not used | Required |
| `vllm_endpoint` | Required (External vLLM) | Not used | Required | Not used |
| `resume_from_checkpoint` | Not applicable | Yes | Yes | Yes |
| `regenerate_responses` | Yes | Not applicable | Yes | Yes |

## Setup

### Setup Workbench

**Step 1.** Access the OpenShift AI dashboard, for example from the top navigation bar menu:

![](../../images/01.png)

**Step 2.** Log in, then go to **_Data Science Projects_** and create a project:

![](../../images/02.png)

**Step 3.** Once the project is created, click on **_Create a workbench_**:

![](../../images/03.png)

**Step 4.** Select the `Training | Jupyter | PyTorch | CUDA | Python` workbench image:

![](../../images/04a.png)

> [!NOTE]
> No GPU is needed on the workbench — it only submits TrainJobs and monitors progress. All training runs on dedicated pods.

**Step 5.** You may want to create a **Hardware Profile** with GPU support, similar to the one below:

![](../../images/04b.png)

**Step 6.** Select the Hardware profile you want to use:

![](../../images/04c.png)

**Step 7.** Create **shared storage** that will be shared between the workbench and the training pods. Make sure it uses a storage class with RWX capability:

![](../../images/04d.png)

> [!NOTE]
> You can attach an existing shared storage if you already have one instead.

**Step 8.** Review the storage configuration and click "Create workbench":

![](../../images/04e.png)

**Step 9.** From "Workbenches" page, click on **_Open_** when the workbench you've just created becomes ready:

![](../../images/05.png)

### Running the example notebooks

- From the workbench, clone this repository: `https://github.com/red-hat-data-services/red-hat-ai-examples.git`
- Navigate to the `examples/fine-tuning/rhoai-3.6/speculator` directory.

Choose one of the mode-specific notebooks:

| Mode | Notebook |
| --- | --- |
| DATA_ONLY | [data-only/speculator-data-only-example.ipynb](data-only/speculator-data-only-example.ipynb) |
| TRAIN_ONLY | [train-only/speculator-train-only-example.ipynb](train-only/speculator-train-only-example.ipynb) |
| OFFLINE | [offline/speculator-offline-example.ipynb](offline/speculator-offline-example.ipynb) |
| ONLINE | [online/speculator-online-example.ipynb](online/speculator-online-example.ipynb) |

> [!NOTE]
>
> - You will need a Hugging Face token if using gated models (e.g., Llama models).
> - Set the `HF_TOKEN` environment variable in your trainer configuration via the `env` parameter.

You can now proceed with the instructions from the notebook.
