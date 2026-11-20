# LoRA GRPO pipeline on Red Hat OpenShift AI

> **Version scope:** Testing and verification of this example are limited to
> **RHOAI 3.6**.

## Overview

This guide walks through importing, configuring, running, and validating the
LoRA GRPO pipeline through the Red Hat OpenShift AI (RHOAI) Dashboard. It uses
Kubeflow Pipelines, Kubeflow Trainer, and Training Hub's ART backend to fine-tune
a model for tool calling on a single GPU.

The pipeline prepares the dataset, trains LoRA adapters and merges them into
the base model, evaluates recorded rewards, and conditionally registers and
deploys the resulting model through Model Registry and KServe.

The underlying pipeline is marked **alpha** and its interface may change. Use
the same pipeline revision for compilation, parameter reference, and validation.

## Prerequisites

- A RHOAI 3.6 cluster with the Dashboard, AI Pipelines, Trainer, Model Registry,
  and KServe model serving configured.
- A project with a running pipeline server and its artifact storage configured.
- A ClusterTrainingRuntime compatible with Training Hub's LoRA GRPO algorithm.
  The pipeline's default runtime name is `training-hub`.
- An existing ReadWriteMany (RWX) PVC in the pipeline project. The serving
  namespace must be the same namespace as this PVC.
- A non-admin user with access to the project and pipeline server, and authorized
  workload identities for training, registration, and deployment.
- Network access and image pull credentials needed by the pipeline components,
  training runtime, model downloads, and serving image.
- For compilation: Git, Python 3.11 or newer, and the pipeline repository's
  Python dependencies. For CLI verification: an authenticated `oc` client.

## Hardware requirements

These are the current pipeline defaults for the example base model
`Qwen/Qwen3-4B`. GPU memory suitability and total storage usage must be confirmed
on the target cluster before treating these settings as validated requirements.

| Purpose | GPU | CPU | Memory | Storage |
| --- | --- | --- | --- | --- |
| TrainJob worker | Exactly 1 NVIDIA GPU | 4 cores | 64Gi | Shared RWX PVC |
| Serving replica | 1 NVIDIA GPU | 2 cores | 8Gi | Same RWX PVC |
| Persistent model and cache storage | — | — | — | At least 50Gi RWX; size for models, caches, and retained runs |

Training and serving are separate stages. The ART backend shares its training
GPU between rollout generation and policy updates. Evaluation reads the
training results; it does not launch a separate GPU benchmark job.

The shared PVC stores models, training outputs, prepared datasets, and runtime
caches. Consider space for these when sizing the PVC.

## Setup

### Administrator responsibilities

Start with a new project and record the setup before handing it to the test user.
Cluster-scoped configuration and grants outside the user's project must be
performed by an administrator.

The administrator owns project and pipeline-server setup, artifact storage, shared
PVC creation, secrets, runtime availability, and other access grants. The
end user imports, configures, runs, monitors, and validates the pipeline, with
read access to runtimes and project PVCs for inspecting prerequisites.

| Setup area | Required result |
| --- | --- |
| Project access | The non-admin user can open the project and manage its pipeline runs. |
| Pipeline server | The project has a ready pipeline server and working artifact storage. |
| Cluster Storage | An RWX PVC is bound, writable by the training workload, and usable by model serving. |
| Runtime and GPU | A compatible ClusterTrainingRuntime is available; the training identity can discover it and the worker can schedule. |
| Training credentials | `kubernetes-credentials` identifies an authorized identity that can submit and monitor TrainJobs in this project. |
| Registry | The selected registry is reachable; the pipeline ServiceAccount has the registry's required access. |
| Serving | The pipeline ServiceAccount can get, create, and patch ServingRuntime and InferenceService resources in the project. |
| Pull access and network | Required images can be pulled and components can reach the API, registry, artifact storage, and dataset/model sources. |

There are three identities to verify separately:

1. **Test user:** uses the Dashboard to import pipelines, start runs, and inspect
   results. Namespace access alone does not establish that pipeline-server access
   is configured correctly.
2. **Training API identity:** comes from the `kubernetes-credentials` Secret.
   Its token is used to discover training runtimes and submit and monitor jobs.
3. **Pipeline ServiceAccount:** runs component pods. Model deployment uses its
   mounted Kubernetes credentials; registry access also needs to be granted to
   the appropriate pipeline ServiceAccount.

Grant only the permissions required by each identity. The test user does not
need cluster-admin access to run this example.

### User access prerequisites

Ask the administrator to provide access to the project, pipeline server, training
runtimes, shared PVC, model registry, and deployment status needed for this
workflow. The example project is `loragrpopipeline`.

The administrator must authorize the workload identities to train, register, and deploy the model before a run starts.

### Create shared storage for GRPO

**Administrator:** provision a separate shared PVC for the GRPO pipeline.
Configuring a pipeline server may create an internal database PVC such as
`mariadb-dspa`. This database volume serves the pipeline infrastructure; it is
not the model/checkpoint PVC selected by `p01_persistent_pvc`.

`oc get pvc -n loragrpopipeline` lists the PVCs your account can see in the
namespace, including storage created for services such as the pipeline server's
database. The RHOAI **Cluster storage** tab is a view of storage managed through
the Dashboard and may omit these internal service PVCs.

For example, the CLI might list only `mariadb-dspa` while the Cluster storage
tab is empty. That PVC stores the pipeline server's database data; its existence
does not provide shared storage for GRPO models, checkpoints, and caches. Leave
it dedicated to the database and create `loragrpopipeline-pvc` separately using
the steps below. Verify that the new claim has **ReadWriteMany (RWX)** access
and at least **50Gi**, then use its actual resource name for `p01_persistent_pvc`.

1. Identify an installed RWX-capable storage class. In the OpenShift console,
   open **Storage → StorageClasses**, or run `oc get storageclass` as admin.
   Confirm the selected provisioner supports ReadWriteMany. If no suitable class is available, have the storage administrator configure a shared-filesystem provisioner before proceeding.
2. In the RHOAI Dashboard, open **Projects → loragrpopipeline → Cluster storage**
   and click **Add cluster storage**.
3. Set the storage name to `loragrpopipeline-pvc`, request at least **50Gi**, and
   select the RWX-capable class verified in step 1. Ensure the resulting access
   mode is **ReadWriteMany**.
4. Create the storage and verify the actual PVC name, capacity, access mode, and provisioning status:

   ```bash
   oc get pvc loragrpopipeline-pvc -n loragrpopipeline
   oc describe pvc loragrpopipeline-pvc -n loragrpopipeline
   ```

**Test user:** confirm the new claim can be read with
`oc get pvc loragrpopipeline-pvc -n loragrpopipeline`. PVC creation remains an admin
action. On the selected cluster, verify `Bound`, at least `50Gi`, `RWX`, and
the selected storage class. Successful workload mounts and writes require an
actual run. Check the class's binding mode and volume-expansion support before
relying on delayed provisioning or later resizing.

### Credentials and data connections

Create secrets in the pipeline project before starting a run.

| Secret | Keys | When required |
| --- | --- | --- |
| `kubernetes-credentials` | `KUBERNETES_SERVER_URL`, `KUBERNETES_AUTH_TOKEN` | Every run; use credentials for the same cluster as the pipeline. |
| `hf-token` | `HF_TOKEN` | Gated or private Hugging Face models/datasets; the token must have access to the selected resources. |
| Connection Secret selected by `p08_dataset_data_connection_name` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`; optionally `AWS_DEFAULT_REGION`, `AWS_S3_ENDPOINT` | Private S3 dataset input. The parameter defaults to `s3-secret`. |

The pipeline server's artifact-storage configuration is separate from the
optional S3 connection used to read a training dataset. A Hugging Face or
PVC-based dataset does not require an S3 dataset connection.

### Model Registry prerequisites

An existing model registry can be reused. It can reside in a different namespace
from the pipeline project; the registry records the model's storage URI, while
the serving workload mounts the shared PVC in `loragrpopipeline`.

Ask the administrator or registry owner to provide:

- An available registry and its connection address and port for
  `p04_model_registry_address` and `p22_model_registry_port`.
- Registry access for the pipeline ServiceAccount used by the registration task.
- Dashboard registry access for the end user to validate the registered model.
- Network connectivity from the pipeline project to the selected endpoint.

Use a unique model name/version pair for each registration. Match the address
scheme and port to the selected endpoint: an HTTPS Route normally uses an
explicit `https://` address and port `443`. The current registration component
disables TLS certificate verification, including for explicit HTTPS addresses;
confirm the connection behavior before running this example.

If a registry needs to be created, the administrator can follow the
[RHOAI registry creation instructions](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/managing_model_registries/creating-a-model-registry_managing-model-registries).

### Generate the pipeline YAML

Compile the full [LoRA GRPO pipeline from the `rhoai-3.6` branch](https://github.com/red-hat-data-services/pipelines-components/tree/rhoai-3.6/pipelines/training/finetuning/lora_grpo).

```bash
git clone --branch rhoai-3.6 --single-branch https://github.com/red-hat-data-services/pipelines-components.git
cd pipelines-components
PYTHONPATH=. python pipelines/training/finetuning/lora_grpo/pipeline.py
```

The output is
`pipelines/training/finetuning/lora_grpo/pipeline.yaml`.
The dependencies belong to the pipeline repository; this guide does not contain
a separate Python application.

## Usage

Before importing, sign in as the test user and confirm the project and its
Pipelines page are accessible.

### 1. Import the pipeline

1. Sign in to the RHOAI Dashboard as the non-admin user.
2. Open **Develop & train → Pipelines → Pipeline definitions** and select the
   project prepared by the administrator.
3. Choose **Import pipeline**, upload the generated `pipeline.yaml`, and give
   the definition a descriptive name, such as `lora-grpo-pipeline`.
4. When replacing a definition, upload a new pipeline version and select that
   version when creating the run.

### 2. Configure the run

Open **Pipelines → Runs → Create run**. Select the project, pipeline definition,
and pipeline version, then enter a run name and configure its parameters.

All six parameters below are required.

| Parameter | Example value | Meaning |
| --- | --- | --- |
| `p01_persistent_pvc` | `loragrpopipeline-pvc` | Existing RWX PVC name, without a path. |
| `p02_dataset_uri` | `hf://Agent-Ark/Toucan-1.5M:Qwen3` | Hugging Face dataset reference, including the `Qwen3` configuration. |
| `p03_training_model` | `Qwen/Qwen3-4B` | Base model to fine-tune. |
| `p04_model_registry_address` | `<registry-service-host>` | Registry endpoint provided by the administrator. Include `https://` for an HTTPS endpoint and set its matching port in `p22_model_registry_port`. |
| `p05_serving_namespace` | `loragrpopipeline` | Same namespace as the pipeline and PVC. |
| `p06_tokenizer_mode` | `slow` | Proposed Qwen3 setting; supported modes are `auto`, `slow`, and `mistral`. Confirm with the selected model and serving image. |

For this example, change these optional parameters:

| Parameter | Example value | Purpose |
| --- | --- | --- |
| `p09_training_num_iterations` | `5` | Number of training updates. A short smoke run does not guarantee reward improvement. |
| `p12_training_lora_r` | `8` | LoRA rank. |
| `p13_training_lora_alpha` | `8` | LoRA scaling. |

Keep the remaining optional parameters at their defaults, listed below. These
settings do not establish a validated training recipe.

| Parameter | Default | Purpose |
| --- | --- | --- |
| `p07_dataset_max_invalid_row_ratio` | `0.10` | Fraction of invalid non-Hugging Face rows allowed, from `0.0` to `1.0`; use `0.0` for strict validation. |
| `p08_dataset_data_connection_name` | `s3-secret` | Connection Secret for private S3 datasets. |
| `p10_training_group_size` | `4` | Candidate rollouts per prompt. |
| `p11_training_prompt_batch_size` | `50` | Prompts per update. |
| `p14_training_n_train` | `200` | Maximum training examples sampled by ART. |
| `p15_training_completion_timeout_seconds` | `7200` | Completion wait after training starts; startup has a separate wait. |
| `p16_training_learning_rate` | `0.00001` | Learning rate. |
| `p17_training_gpu_memory_utilization` | `0.45` | Fraction reserved for the rollout engine. |
| `p18_training_enforce_eager` | `true` | Eager vLLM execution; keep enabled for the proposed Qwen3 example. |
| `p19_training_env_vars` | Empty | Comma-separated `KEY=VALUE` environment variables for the training pod. |
| `p20_model_registry_name` / `p21_model_registry_version` | `grpo-model` / `1.0.0` | Choose a unique model/version pair for each registration. |
| `p22_model_registry_port` | `8080` | Must match the selected registry's port. |
| `p23_serving_gpu_count` | `1` | GPUs per serving replica. |
| `p24_serving_max_model_len` | `4096` | Serving context length. |
| `p25_serving_max_replicas` / `p39_serving_min_replicas` | `1` / `1` | Must satisfy `1 <= min_replicas <= max_replicas`. |
| `p26_serving_cpu_requests` / `p27_serving_memory_requests` | `2` / `8Gi` | Serving CPU/memory; each value is used for both requests and limits. |
| `p28_training_data_config` | Empty | Hugging Face dataset configuration when not included in the URI; leave empty when the URI already includes `:Qwen3`. |
| `p29_training_cpu` / `p31_training_memory` | `4` / `64Gi` | Training worker CPU and memory requests. |
| `p30_training_gpu` | `1` | Keep at exactly one GPU for ART. |
| `p32_training_labels` / `p33_training_annotations` | Empty / Empty | Comma-separated `key=value` worker labels or annotations. |
| `p34_training_runtime` | `training-hub` | Must match the installed compatible runtime. |
| `p35_model_registry_author` | `pipeline` | Author stored in the registry entry. |
| `p36_model_registry_description` | Empty | Description stored in the registry entry. |
| `p37_model_registry_format_name` / `p38_model_registry_format_version` | `pytorch` / `1.0` | Registered model format and format version. |

These tables cover all 39 pipeline parameters. Check the parameter descriptions
in the imported definition against the revision you compiled.

The rollout batch is `prompt_batch_size × group_size`, or 200 with the defaults.
The LoRA weight scale is `lora_alpha / lora_r`. Increasing batch/group size,
model size, or iteration count affects resource usage or run duration; adjust
resources and the completion timeout accordingly. The timeout is a maximum
wait in seconds and returns as soon as the TrainJob completes or fails.

### 3. Run and inspect results

Click **Run** and open the run graph. Inspect the task logs and outputs as each
stage finishes:

1. Replica validation checks the serving replica bounds.
2. Dataset preparation resolves the source and normalizes non-Hugging Face data.
3. Training submits a TrainJob, waits for completion, and persists the merged
   model and training results on the shared PVC.
4. GRPO evaluation reads the recorded training metrics and determines promotion.
5. If promotion passes, model registration runs and then model deployment creates or updates
   the serving resources.

Select the evaluation task's metrics and `output_reward_chart` artifact to
inspect the recorded reward history.

| Metric | Interpretation |
| --- | --- |
| `initial_reward` | First recorded reward observation. |
| `final_reward` | Last recorded reward observation. |
| `reward_improvement` | Final reward minus initial reward. |
| `mean_reward` | Mean reward across recorded observations. |
| `full_match_rate` | Last recorded full-match rate for tool calls. |
| `training_iterations` | Number of recorded reward observations. |
| `promotion_passed` | `1` when promotion passes, otherwise `0`. |

Promotion requires at least two recorded reward observations and
`final_reward > initial_reward`. A run can finish successfully with registration
and deployment skipped when the model does not pass this gate. These metrics
describe the training run; they are not an independent held-out benchmark.

## Expected outcomes

### Verify the registered model

For a promoted run, open **AI hub → Models →  Registry**, select the configured registry,
and locate the model name and version entered for this run. Check its metrics,
pipeline provenance, and model storage URI. The URI should refer to the
run-specific model directory:

### Verify the deployed model

The serving resource name is derived from the base model name. With
`Qwen/Qwen3-4B`, both the ServingRuntime and InferenceService are named `qwen3-4b`.

Run these checks as the non-admin user, replacing the project placeholder:

```bash
oc -n <pipeline-project> get servingruntime qwen3-4b
oc -n <pipeline-project> get inferenceservice qwen3-4b
oc -n <pipeline-project> get inferenceservice qwen3-4b \
  -o jsonpath='{.spec.predictor.model.storageUri}{"\n"}'
oc -n <pipeline-project> get inferenceservice qwen3-4b \
  -o jsonpath='{.status.conditions}{"\n"}{.status.url}{"\n"}'
```

Confirm `Ready=True` and that the storage URI points to this run's model
directory. The deployment task also outputs the inference API URL.

Repeated promoted runs for the same base model in the same namespace update
the existing endpoint. Run-specific model directories do not create distinct
serving endpoints. Use separate projects to isolate concurrent demonstrations.

The current deployment component disables endpoint authentication. Confirm the
resulting endpoint's access and network exposure with the administrator before
using sensitive data in this example.

**Pending live validation:** add the tested inference request and response,
and screenshots in [docs/](docs/) of import, parameters, the run graph, RL metrics/reward chart,
registry entry, and ready deployment. Capture the Hugging Face dataset run and show how
to recognize a run that does not pass promotion.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| User cannot import or run | Verify project membership and pipeline-server permissions using the non-admin identity. |
| Runtime missing or API returns 403 during training | Check the identity in `kubernetes-credentials`, token expiry, runtime discovery access, and TrainJob permissions. |
| Registry or deployment returns 403 | Check the pipeline ServiceAccount's grants in the registry namespace and serving project. |
| PVC pending, mount failure, or permission denied | Check RWX support, storage quota, namespace, and workload write access. |
| Training pod pending | Check GPU availability, resource quota, node placement, and runtime settings. |
| Out-of-memory failure | Review batch/group size, rollout GPU memory utilization, and model size. |
| Dataset validation fails | Check the Hugging Face repository ID, dataset configuration, required access token, and Training Hub loader error. |
| Registration and deployment skipped | Inspect `promotion_passed` and reward history before treating this as an error. |
| Serving fails | Inspect InferenceService conditions and predictor logs; check the model URI, image pull access, GPU capacity, and tokenizer mode. |
