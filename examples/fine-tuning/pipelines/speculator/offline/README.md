# Offline Pipeline (external vLLM, extraction + training in one run)

> [!WARNING]
>
> **Stability: alpha** — this pipeline may change. Re-generate the YAML after pulling upstream changes.

This guide covers the **speculator-offline-pipeline** — extraction and training combined in a single run, with hidden states extracted by an **external, user-managed vLLM endpoint** instead of a managed sidecar.

## When to use this pipeline

- **You already run vLLM.** Point the pipeline at your existing deployment and skip the managed sidecar entirely.
- **You need custom vLLM configuration** the managed sidecar doesn't expose.
- No external vLLM and want one run? Use [online](../online/). Want to iterate on training without re-extracting? Use [data-extraction](../data-extraction/) + [train-only](../train-only/).

## How it works

The offline pipeline combines data-only extraction and train-only training in a single run — it creates hidden states and processed training data itself, so pre-existing extraction artifacts are not required:

1. **Extraction** sends requests to the external vLLM endpoint at `p03_vllm_endpoint`. No managed sidecar is launched. Hidden states are written to `p11_hidden_states_path` and processed data below `p10_output_dir`.
2. **Training** reads processed data from `p12_training_data_path` and hidden states from `p11_hidden_states_path`.
3. **Evaluate** with GuideLLM.
4. **Register** — optional; leave `p47_model_registry_address` empty to skip.
5. **Serve** via a cluster-local KServe InferenceService using the verifier at `p02_verifier_model_pvc` and the draft at `final_model`.

The completed draft is written to `pvc://<p01_persistent_pvc>/final_model`. Each run **replaces** this shared path — use a separate PVC per revision if earlier registry versions must keep referencing their original weights.

`p01_persistent_pvc` is an existing ReadWriteMany PVC in the pipeline namespace, mounted at `/mnt/persistent`, storing the verifier, datasets, extraction outputs, checkpoints, and final draft. It must also be available in `p06_serving_namespace`. With `p01_persistent_pvc="shared"`, `p10_output_dir="speculator-output"` resolves to `pvc://shared/speculator-output`.

## Hardware requirements (Qwen3-0.6B)

| Component | GPU | CPU | Memory |
| --- | --- | --- | --- |
| Extraction + training worker | 1 (`p34`) | 4 cores | 64Gi |
| External vLLM | your own — size separately | — | — |
| Evaluation / serving | ~1 | — | — |

Extraction and training share one runtime (`p37_job_runtime`, default `speculator-model-opt-cuda`) and one set of env overrides / packages (`p36_job_envs`, `p38_packages_to_install`).

## Setup

Work through the [shared prerequisites](../README.md#prerequisites), plus the offline-specific ones:

### External vLLM server

`p03_vllm_endpoint` must point at a vLLM deployment that:

- is reachable from the pipeline namespace,
- can access the verifier and hidden-state paths on `p01_persistent_pvc`,
- serves the verifier model you intend to train against.

Verify reachability from the project namespace before running:

```bash
oc run vllm-probe --rm -it --restart=Never --image=curlimages/curl -- \
  curl -s <p03_vllm_endpoint>/v1/models
```

If the probe fails with an image pull error on a restricted cluster, substitute any image your cluster serves that contains curl. If it fails to connect, fix networking (NetworkPolicy, endpoint URL) before running the pipeline — the pipeline's first extraction request will fail the same way.

### Verifier already on the PVC

`p02_verifier_model_pvc` must identify the relative verifier directory, and the model must already exist there. **This pipeline does not download models from HuggingFace.** Cache it once either by:

- running the [data-extraction pipeline](../data-extraction/) with `p04_download_model=true` (its guide shows how to verify the cached path), or
- copying the model to the PVC manually.

The cache path follows the `models/<org>--<model>` naming (model ID with `/` replaced by `--`), e.g. `models/Qwen--Qwen3-0.6B`.

### Remaining prerequisites

- CTR `speculator-model-opt-cuda`
- Model Registry + RoleBinding + serving namespace permissions — only if you keep registration enabled

> [!IMPORTANT]
>
> `p15_target_layer_ids` is **required** in offline mode — four comma-separated layer IDs matching the verifier. The SDK cannot auto-detect layer IDs from the PVC-backed verifier. For Qwen3-0.6B: `2,14,25,28`. Layer IDs are verifier-specific — look them up per model, do not reuse Qwen's IDs for a different architecture.

## Dataset

`p04_dataset_name` accepts the built-ins `magpie` (Magpie-Align/Magpie-Llama-3.1-Pro-300K-Filtered), `ultrachat` (HuggingFaceH4/ultrachat_200k), and `gsm8k` (openai/gsm8k), or a JSON/JSONL dataset already on the PVC (`pvc://<pvc-name>/<path>`). Only these built-ins and local files are supported in offline mode. `p07_data_extraction_max_samples=0` processes all examples; keep `p09_data_extraction_concurrency=1` on shared/NFS storage.

## Key OFFLINE configuration

### Path alignment

Extraction writes to `p10_output_dir` / `p11_hidden_states_path`; training reads from `p12_training_data_path` / `p11_hidden_states_path`. Defaults line up (`speculator-output` and `speculator-output/hidden_states`). If you change `p10_output_dir`, update `p12_training_data_path` and `p11_hidden_states_path` to match.

### Not used in OFFLINE

There is no model download — no `download_model` parameter. No managed sidecar — no vLLM sidecar resource parameters. The external endpoint's resources are your responsibility.

## Running the pipeline

**Step 1 — generate the pipeline YAML.** Follow [Generate the pipeline YAML](../README.md#1-generate-the-pipeline-yaml) in the common guide, compiling the `offline` mode:

```bash
PYTHONPATH=$(pwd) python pipelines/training/speculator/offline/pipeline.py
```

This writes `pipelines/training/speculator/offline/pipeline.yaml`.

**Step 2 — import it into Red Hat OpenShift AI.** Follow the click-by-click instructions in [Import the pipeline into Red Hat OpenShift AI](../README.md#3-import-the-pipeline-into-red-hat-openshift-ai). The imported definition is named `speculator-offline-pipeline`.

**Step 3 — create a run.** Open the pipeline definition, click **Create run**, and fill in the parameters from the table below. Leave everything not listed at its default. Use a new `p50_model_registry_version` per revision if registering.

![Create run dialog with offline parameters](../docs/rhoai-create-run.png)
> **Screenshot needed:** `docs/rhoai-create-run.png` — the **Create run** dialog with the offline parameter form (see the common guide's slot; one shared parameter-form screenshot is used across modes).

**Step 4 — start the run and watch it.** Click **Start** and follow it as [described in the common guide](../README.md#5-watch-the-run). The graph runs extract → train → evaluate → register (optional) → serve, all against your external vLLM for the extraction stage.

### Example: Qwen3-0.6B

Assumes the verifier was already cached on the PVC (e.g., by a prior data-extraction run):

| Parameter | Value | Notes |
| --- | --- | --- |
| `p01_persistent_pvc` | `shared` | Your existing RWX PVC name |
| `p02_verifier_model_pvc` | `models/Qwen--Qwen3-0.6B` | Must already exist on the PVC |
| `p03_vllm_endpoint` | `http://vllm.my-namespace.svc:8000` | Your external vLLM service |
| `p04_dataset_name` | `ultrachat` | Built-in dataset |
| `p05_evaluation_dataset_uri` | `HuggingFaceH4/ultrachat_200k` | HF dataset ID or PVC JSONL |
| `p06_serving_namespace` | `<pvc-namespace>` | Must access the PVC |
| `p15_target_layer_ids` | `2,14,25,28` | **Required** |
| `p47_model_registry_address` | `""` | Empty skips registration |

Training/evaluation/resource parameters can keep their defaults for a first run.

## Interpreting the results

Same evaluation task and metrics as the train-only pipeline — see [Interpreting the evaluation results](../train-only/README.md#interpreting-the-evaluation-results) in that guide for the full metric table and how to read it.

## Testing the served endpoint

Follow [Testing the served endpoint](../README.md#testing-the-served-endpoint) in the common guide. One offline-specific note: KServe may scale the predictor to zero after a period of idleness — check `oc get inferenceservice -n <p06_serving_namespace>` shows `True` before concluding something is broken.

## Customization

Sweep `p16_training_epochs`, `p17_training_lr`, `p19_training_num_layers`, and `p43_evaluation_num_speculative_tokens` between runs. Each offline run repeats extraction — to iterate on training alone, split into [data-extraction](../data-extraction/) + [train-only](../train-only/).

## Full Parameter Reference

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `p01_persistent_pvc` | `str` | `None` | Required name of the existing ReadWriteMany PVC in the pipeline namespace. Stores the verifier, datasets, extraction outputs, checkpoints, and final draft; KServe must also access it in `p06_serving_namespace`. Mounted at `/mnt/persistent`. |
| `p02_verifier_model_pvc` | `str` | `None` | Required verifier model directory on the PVC. The model must already exist there; this pipeline does not download verifier models. |
| `p03_vllm_endpoint` | `str` | `None` | Required URL for the external vLLM service. It must be able to access the verifier and hidden-state paths on `p01_persistent_pvc`. |
| `p04_dataset_name` | `str` | `None` | Required built-in dataset name (`magpie`, `ultrachat`, `gsm8k`) or PVC URI to a JSON/JSONL file. |
| `p05_evaluation_dataset_uri` | `str` | `None` | Required Hugging Face dataset ID or local JSON/JSONL file. `pvc://` URIs must reference `p01_persistent_pvc`. |
| `p06_serving_namespace` | `str` | `None` | Required KServe namespace; must access the PVC. |
| `p07_data_extraction_max_samples` | `int` | `0` | Maximum extraction examples; `0` processes the full dataset. |
| `p08_data_extraction_regenerate_responses` | `bool` | `False` | Regenerate assistant responses with the verifier; built-in datasets only. |
| `p09_data_extraction_concurrency` | `int` | `1` | Extraction request concurrency and training `datagen_concurrency`. Use `1` on shared/NFS PVCs. |
| `p10_output_dir` | `str` | `speculator-output` | PVC-relative directory for extraction output, processed training data, and checkpoints. |
| `p11_hidden_states_path` | `str` | `speculator-output/hidden_states` | Hidden-state directory written by extraction and read by training. Keep aligned with the output directory. |
| `p12_training_data_path` | `str` | `speculator-output` | Directory containing the processed dataset written by extraction. Keep aligned with `p10_output_dir`. |
| `p13_total_seq_len` | `int` | `2048` | Positive maximum sequence length for extraction, training, and serving. |
| `p14_speculator_type` | `str` | `eagle3` | Draft architecture; the current Trainer and evaluator support `eagle3`. |
| `p15_target_layer_ids` | `str` | `""` | Required in offline mode. Four comma-separated layer IDs matching the verifier. |
| `p16_training_epochs` | `int` | `3` | Number of training epochs. |
| `p17_training_lr` | `float` | `0.0001` | Learning rate for draft-model training. |
| `p18_training_draft_vocab_size` | `int` | `0` | Draft vocabulary size. `0` lets the Trainer SDK derive it. |
| `p19_training_num_layers` | `int` | `1` | Number of layers in the draft model. |
| `p20_training_test_time_steps` | `int` | `1` | Number of test-time training steps configured for Speculator. |
| `p21_training_norm_before_residual` | `bool` | `True` | Apply normalization before the residual connection. |
| `p22_training_norm_before_fc` | `bool` | `False` | Apply normalization before the fully connected layer. |
| `p23_training_embed_requires_grad` | `bool` | `False` | Whether draft embedding weights are trainable. |
| `p24_training_hidden_states_dtype` | `str` | `bfloat16` | Hidden-state dtype; must match the verifier model. |
| `p25_training_scheduler_type` | `str` | `linear` | LR scheduler: `linear`, `cosine`, or `none`. |
| `p26_training_scheduler_warmup_steps` | `int` | `0` | Warmup steps; `0` lets the SDK calculate them. |
| `p27_training_scheduler_total_steps` | `int` | `0` | Total scheduler steps; `0` lets the SDK calculate them. |
| `p30_training_save_best` | `bool` | `False` | Save the best checkpoint by validation loss. |
| `p32_training_resume_from_checkpoint` | `bool` | `False` | Resume from a saved checkpoint when supported by the runtime. |
| `p33_training_resource_cpu` | `str` | `4` | CPU request for the training worker. |
| `p34_training_resource_gpu` | `int` | `1` | Number of GPUs requested for the training worker. |
| `p35_training_resource_memory` | `str` | `64Gi` | Memory request for the training worker. |
| `p36_job_envs` | `str` | `NCCL_DEBUG=INFO,PYTHONUNBUFFERED=1` | Comma-separated `KEY=VALUE` environment overrides shared by extraction and training jobs. |
| `p37_job_runtime` | `str` | `speculator-model-opt-cuda` | ClusterTrainingRuntime shared by hidden-state extraction and draft training. |
| `p38_packages_to_install` | `str` | `""` | Comma-separated Python packages installed in extraction and training jobs. |
| `p40_evaluation_max_samples` | `int` | `80` | Maximum GuideLLM requests per evaluation sweep point; must be positive. |
| `p41_evaluation_max_tokens` | `int` | `256` | Maximum tokens generated per evaluation request; must be positive. |
| `p42_evaluation_temperature` | `float` | `0.0` | Sampling temperature passed to GuideLLM; `0` is deterministic. |
| `p43_evaluation_num_speculative_tokens` | `int` | `5` | Draft tokens proposed per step in evaluation and serving. |
| `p44_evaluation_gpu_memory_utilization` | `float` | `0.9` | GPU memory fraction for evaluation and serving, in `(0, 1]`. |
| `p45_evaluation_startup_timeout_seconds` | `int` | `900` | Maximum wait for the evaluation vLLM server to become ready. |
| `p47_model_registry_address` | `str` | `""` | Model Registry hostname only. Empty (default) skips registration. |
| `p48_model_registry_port` | `int` | `8080` | HTTP REST service port of the registry endpoint. |
| `p49_model_registry_name` | `str` | `speculator-offline-draft` | Name assigned to the registered draft model. |
| `p50_model_registry_version` | `str` | `1.0.0` | Version label for this registration; new value per revision. |
| `p51_serving_endpoint_name` | `str` | `speculator-offline` | DNS-compatible name for the KServe InferenceService. |
| `p52_serving_runtime_image` | `str` | `registry.redhat.io/rhaii-fast/vllm-cuda-rhel9@sha256:97c7d6f66f3f0897b3ff10ddd135de930d45bdd116cf41a43e3ad7270029116a` | Pinned compatible vLLM CUDA image pull spec used by KServe. |

## Troubleshooting

| Symptom | Diagnosis | Fix |
| --- | --- | --- |
| Extraction fails: cannot connect to endpoint | Wrong `p03_vllm_endpoint` or network policy blocks it | Verify the URL from a probe pod in the pipeline namespace (see [Setup](#external-vllm-server)) |
| Extraction succeeds but training fails: hidden states not found | Path misalignment between extraction output and training input | Align `p10`/`p11`/`p12` — changing `p10_output_dir` requires updating the other two |
| Training fails with a layer/tensor shape mismatch | `p15_target_layer_ids` doesn't match the verifier | Set the four layer IDs for your verifier (`2,14,25,28` for Qwen3-0.6B) |
| Verifier not found | `p02_verifier_model_pvc` doesn't exist — this pipeline never downloads | Cache the verifier first; see [Verifier already on the PVC](#verifier-already-on-the-pvc) |
| Registry task fails | Wrong host/port split or missing RoleBinding | Hostname only in `p47`; port in `p48`; add the RoleBinding — or leave the address empty to skip |
| Older registry versions break after re-run | `final_model` overwritten each run | Separate PVC per revision |
| First request to the endpoint hangs or is refused | KServe scaled the predictor to zero, or vLLM is still loading | Check `oc get inferenceservice` shows `True`; wait and retry |

Compile-time problems and endpoint-access problems are covered in the [common troubleshooting table](../README.md#troubleshooting).

## Source

Pipeline source: [`pipelines-components/pipelines/training/speculator/offline`](https://github.com/red-hat-data-services/pipelines-components/tree/main/pipelines/training/speculator/offline). The parameter table above is derived from that directory's `README.md` and `pipeline.py`; re-check it against your imported definition after pulling upstream changes.
