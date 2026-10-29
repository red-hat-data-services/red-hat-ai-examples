# Hidden State Extraction Pipeline (DATA_ONLY)

> [!WARNING]
>
> **Stability: alpha** — this pipeline may change. Re-generate the YAML after pulling upstream changes.

This guide covers the **speculator-hidden-state-extraction-pipeline** — the first step of the two-step speculator workflow. It extracts verifier hidden states for Eagle3 draft-model training. It does **not** train.

## When to use this pipeline

- **Extract once, iterate many.** Hidden-state extraction is the expensive, one-time part of draft-model training. Run this pipeline once, then re-run the [train-only pipeline](../train-only/) as many times as you like while tuning hyperparameters — without paying for extraction again.
- Skip it entirely if you want a single-run workflow — use the [online](../online/) or [offline](../offline/) pipelines instead.

## How it works

1. (Optional) A **download-model** task pulls `p02_verifier_model` from HuggingFace onto the PVC when `p04_download_model` is true.
2. A single **Trainer job** runs the extraction. Depending on `p10_vllm_mode`:
   - **managed** — the Trainer job includes a vLLM sidecar that serves the verifier on the fly.
   - **remote** — extraction talks to your external vLLM endpoint at `p11_vllm_endpoint`.
3. Hidden states are written to the PVC. Managed mode writes under `<p06_output_dir>/hidden_states`; remote mode writes to `p07_hidden_states_path`.

Relative storage paths resolve against `p01_persistent_pvc`. For example, with `p01_persistent_pvc="shared"`, `p06_output_dir="speculator-output"` resolves to `pvc://shared/speculator-output`.

> [!TIP]
>
> The zero-padded `pNN_` parameter prefixes exist only to preserve a logical order in the KFP UI, which sorts inputs alphabetically.

## Hardware requirements (Qwen3-0.6B)

| Mode | GPUs needed |
| --- | --- |
| managed vLLM | 1 (the sidecar; exactly 1 supported) |
| remote vLLM | 0 — your external endpoint owns its own GPUs |

Sidecar defaults: 96Gi memory, `gpu_memory_utilization=0.9`.

## Setup

Work through the [shared prerequisites](../README.md#prerequisites) first:

- Existing RWX PVC (`p01_persistent_pvc`)
- Pipeline server configured for the project
- `kubernetes-credentials` secret (required)
- CTR: `vllm-extract-cuda` for managed mode, `speculator-model-opt-cuda` for remote mode — check with `oc get clustertrainingruntimes`

## Running the pipeline

**Step 1 — generate the pipeline YAML.** Follow [Generate the pipeline YAML](../README.md#1-generate-the-pipeline-yaml) in the common guide, compiling the `data_extraction` mode:

```bash
PYTHONPATH=$(pwd) python pipelines/training/speculator/data_extraction/pipeline.py
```

This writes `pipelines/training/speculator/data_extraction/pipeline.yaml`.

**Step 2 — import it into Red Hat OpenShift AI.** Follow the click-by-click instructions in [Import the pipeline into Red Hat OpenShift AI](../README.md#3-import-the-pipeline-into-red-hat-openshift-ai). The imported definition is named `speculator-hidden-state-extraction-pipeline`.

**Step 3 — create a run.** Open the pipeline definition, click **Create run**, and fill in the parameters from the table below. Leave everything not listed at its default.

![Create run dialog with data-extraction parameters](../docs/rhoai-create-run.png)
> **Screenshot needed:** `docs/rhoai-create-run.png` — the **Create run** dialog with the data-extraction parameter form filled for a Qwen3-0.6B smoke test (see the common guide's slot; one shared parameter-form screenshot is used across modes).

**Step 4 — start the run and watch it.** Click **Start**, then follow the run in the UI as [described in the common guide](../README.md#5-watch-the-run). With the smoke-test values below (16 samples, Qwen3-0.6B, managed vLLM), expect the run to complete in minutes — most of it is the vLLM sidecar loading the verifier.

### Example: Qwen3-0.6B

Minimal managed-mode parameter set for a smoke-test run:

| Parameter | Value | Notes |
| --- | --- | --- |
| `p01_persistent_pvc` | `shared` | Your existing RWX PVC name |
| `p02_verifier_model` | `Qwen/Qwen3-0.6B` | Downloaded because `p04_download_model=true` |
| `p04_download_model` | `true` | Cache the verifier on the PVC |
| `p05_dataset_name` | `ultrachat` | Built-in dataset |
| `p08_max_samples` | `16` | Smoke test; set `0` for the full dataset |
| `p10_vllm_mode` | `managed` | Sidecar vLLM |
| `p18_target_layer_ids` | `2,14,25,28` | **Required** — download mode cannot infer layer IDs |

Everything else can keep its default. For remote mode instead, see [Managed vs remote vLLM](#managed-vs-remote-vllm).

## Verifying the output on the PVC

Before handing off to the train-only pipeline, check what extraction actually produced. This is the gate between the two steps — training fails immediately if the hidden states are missing, so two minutes here saves a confusing failure there.

Run these from any pod that mounts the PVC — a workbench terminal in the project is the natural choice. (If the PVC is mounted at a different path in your workbench, adjust `PVC_MOUNT`; `/opt/app-root/src` is the Red Hat OpenShift AI workbench default.)

```bash
PVC_MOUNT=/opt/app-root/src

# What the extraction run produced:
ls -laR $PVC_MOUNT/speculator-output | head -40

# The hidden states — count and size of the safetensors files:
ls -la $PVC_MOUNT/speculator-output/hidden_states/

# Where the verifier was cached by the download task
# (model ID with "/" replaced by "--"):
ls $PVC_MOUNT/models/
```

What you should see:

- **`speculator-output/hidden_states/`** containing `.safetensors` files — one per target layer of the four in `p18_target_layer_ids`. Each file should be non-trivially sized (tens of MB for the smoke test; more with `p08_max_samples=0`).
- **Processed dataset files** under `speculator-output/` — the preprocessed training data the train-only pipeline reads.
- **`models/Qwen--Qwen3-0.6B/`** — the cached verifier (this path is what `p06_verifier_model_pvc` needs in the train-only run).

If `hidden_states/` is empty or missing, the extraction did not do what you expected — see [Troubleshooting](#troubleshooting) before re-running.

If `safetensors` is available in the workbench, peek at one tensor to confirm the data is real:

```bash
python3 - <<'EOF'
from safetensors import safe_open
from pathlib import Path
files = sorted(Path("/opt/app-root/src/speculator-output/hidden_states").rglob("*.safetensors"))
print(f"{len(files)} file(s):", [f.name for f in files])
with safe_open(files[0], framework="numpy") as f:
    for key in list(f.keys())[:3]:
        print(key, f.get_tensor(key).shape)
EOF
```

For Qwen3-0.6B the shapes should be `[num_samples, seq_len, 1024]` (`hidden_size=1024`).

## Managed vs remote vLLM

### Method 1: Managed vLLM sidecar (`p10_vllm_mode=managed`)

The pipeline adds a vLLM sidecar to the Trainer job. No infrastructure beyond the CTR is needed. When `p04_download_model=false`, managed mode reuses `p03_verifier_model_pvc` if set, or passes `p02_verifier_model` directly to vLLM.

### Method 2: External vLLM endpoint (`p10_vllm_mode=remote`)

Point `p11_vllm_endpoint` at your own vLLM deployment. Requirements:

- The external service must be able to access the verifier at `p03_verifier_model_pvc` on the shared PVC (remote mode always requires the PVC-backed path).
- Set `p07_hidden_states_path` to match the location the remote vLLM service uses for hidden states on the shared PVC — it must line up with what the service writes.
- Use the `speculator-model-opt-cuda` CTR (`p23_job_runtime`).

Test that the endpoint is reachable from the project namespace before running:

```bash
oc run vllm-probe --rm -it --restart=Never --image=curlimages/curl -- \
  curl -s <p11_vllm_endpoint>/v1/models
```

## Verifier model and target layer IDs

`p18_target_layer_ids` must be exactly **four** comma-separated verifier layer indices. It is required when using `p03_verifier_model_pvc`, when `p04_download_model` is true, or in remote mode. It may be omitted **only** in managed mode when the verifier is passed as a HuggingFace model ID and not downloaded — the SDK can then infer indices from the model config. For Qwen3-0.6B: `2,14,25,28`.

The IDs are **verifier-specific** — for any other model (e.g. Llama-3.2-1B-Instruct), look up that model's four Eagle3 target layers; do not reuse Qwen's IDs across architectures. A wrong set fails at training time with a tensor shape mismatch.

## Dataset

`p05_dataset_name` accepts the built-ins `magpie` (Magpie-Align/Magpie-Llama-3.1-Pro-300K-Filtered), `ultrachat` (HuggingFaceH4/ultrachat_200k, default), and `gsm8k` (openai/gsm8k), or a JSON/JSONL file on the PVC (relative path or `pvc://<claim>/<path>`). Arbitrary HuggingFace dataset IDs are not supported.

## Full Parameter Reference

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `p01_persistent_pvc` | `str` | `None` | Name of the existing PVC in the pipeline namespace, mounted at `/mnt/persistent`, that stores models, datasets, and extraction outputs. Required. |
| `p02_verifier_model` | `str` | `""` | Hugging Face Hub model ID. Set when `p04_download_model` is true to download to the PVC. In managed mode with downloads disabled and no PVC path set, this ID is passed directly to vLLM. |
| `p03_verifier_model_pvc` | `str` | `""` | Optional verifier directory on `p01_persistent_pvc`. Managed mode with downloads disabled reuses it if set. Remote mode always requires this PVC-backed path. Relative path or `pvc://` URI. |
| `p04_download_model` | `bool` | `False` | Download `p02_verifier_model` to the PVC. |
| `p05_dataset_name` | `str` | `ultrachat` | `magpie`, `ultrachat`, or `gsm8k`; or a JSON/JSONL file on the PVC. Arbitrary HuggingFace dataset IDs are not supported. |
| `p06_output_dir` | `str` | `speculator-output` | Directory on `p01_persistent_pvc` where extraction outputs are written. |
| `p07_hidden_states_path` | `str` | `speculator-output/hidden_states` | Remote-mode output location for hidden states; must match the location used by the remote vLLM service. Managed mode ignores it and writes to `<p06_output_dir>/hidden_states`. |
| `p08_max_samples` | `int` | `16` | Maximum samples to process; `0` processes the full dataset. |
| `p09_regenerate_responses` | `bool` | `False` | Re-generate assistant responses with the verifier instead of using the originals. Built-in datasets only. |
| `p10_vllm_mode` | `str` | `managed` | `managed` (sidecar) or `remote` (external service). |
| `p11_vllm_endpoint` | `str` | `""` | URL of the external vLLM service; required for `remote`, blank for `managed`. |
| `p12_vllm_resource_gpu` | `int` | `1` | GPUs requested by managed vLLM; the SDK currently supports exactly `1`. |
| `p13_vllm_resource_memory` | `str` | `96Gi` | Memory requested by the managed vLLM sidecar. |
| `p14_vllm_gpu_memory_utilization` | `float` | `0.9` | Fraction of GPU memory available to vLLM, in `(0, 1]`. |
| `p15_vllm_readiness_timeout_minutes` | `int` | `60` | Maximum wait for the vLLM endpoint to become ready, in minutes; minimum `1`. |
| `p16_total_seq_len` | `int` | `2048` | Maximum sequence length for preprocessing and extraction; must be positive. |
| `p17_speculator_type` | `str` | `eagle3` | Draft architecture; `eagle3` is the only supported type. |
| `p18_target_layer_ids` | `str` | `""` | Exactly four comma-separated verifier layer indices. See [Verifier model and target layer IDs](#verifier-model-and-target-layer-ids). |
| `p19_data_extraction_concurrency` | `int` | `1` | Concurrent vLLM requests for extraction; use `1` on shared or NFS storage. |
| `p20_packages_to_install` | `str` | `""` | Comma-separated Python packages to install in the job. |
| `p21_pip_index_urls` | `str` | `""` | Comma-separated package-index URLs for job installs. |
| `p22_job_envs` | `str` | `NCCL_DEBUG=INFO,PYTHONUNBUFFERED=1` | Comma-separated `KEY=VALUE` environment overrides for the job. |
| `p23_job_runtime` | `str` | `vllm-extract-cuda` | Name of the runtime used by the extraction job. |

## Troubleshooting

| Symptom | Diagnosis | Fix |
| --- | --- | --- |
| Run fails waiting for vLLM to become ready (timeout) | Sidecar crashed or is slow to load the verifier | Check the Trainer pod logs; raise `p15_vllm_readiness_timeout_minutes`; verify GPU memory fits the verifier |
| Cannot connect to remote vLLM endpoint | Wrong `p11_vllm_endpoint`, or network policy blocks the path | Verify the URL from a test pod in the pipeline namespace (see probe command above) |
| Extraction completes but hidden states are empty | Managed/remote path mismatch, or `p08_max_samples=0` semantics misunderstood | Managed mode writes to `<p06_output_dir>/hidden_states`; in remote mode align `p07_hidden_states_path` with the service's write location |
| Run fails with ClusterTrainingRuntime not found | Wrong CTR for the mode | Managed needs `vllm-extract-cuda`; remote needs `speculator-model-opt-cuda` |
| Extraction slow on shared storage | Concurrent I/O saturating NFS | Keep `p19_data_extraction_concurrency=1` |
| Download task fails with 401 | Gated model without `hf-token` secret | Create the `hf-token` secret |

Compile-time problems (`ModuleNotFoundError`, storage class, package-index issues) are covered in the [common troubleshooting table](../README.md#troubleshooting).

## Source

Pipeline source: [`pipelines-components/pipelines/training/speculator/data_extraction`](https://github.com/red-hat-data-services/pipelines-components/tree/main/pipelines/training/speculator/data_extraction). The parameter table above is derived from that directory's `README.md` and `pipeline.py`; re-check it against your imported definition after pulling upstream changes.
