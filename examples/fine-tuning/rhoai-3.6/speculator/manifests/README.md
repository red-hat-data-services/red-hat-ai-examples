# External vLLM Server for Hidden State Extraction

This guide covers deploying, verifying, customizing, and cleaning up the external
vLLM server used by the speculator training examples. It is shared by:

- **OFFLINE mode** — [offline notebook](../offline/speculator-offline-example.ipynb)
- **DATA_ONLY mode, Method 2 (external vLLM endpoint)** — [data-only notebook](../data-only/speculator-data-only-example.ipynb)

Both workflows need a running vLLM server that can extract hidden states from the
verifier model. The SDK does not deploy this server for you — you manage it.

## What This Server Is

The manifest [`vllm-server.yaml`](vllm-server.yaml) deploys a vLLM instance
configured for hidden state extraction:

- `speculative-config` with `method: extract_hidden_states` and the Eagle3
  auxiliary hidden state layer IDs (`SPECULATOR_TARGET_LAYER_IDS`)
- `ExampleHiddenStatesConnector` in `kv_producer` role, writing extracted hidden
  state tensors to shared storage (`SPECULATOR_HS_PATH`)
- The pinned image `quay.io/aipcc/rhaiis/cuda-ubi9:3.6` — a vLLM build that
  includes the extraction support above; upstream vLLM images do not have it,
  so do not swap the image without verifying extraction support

It creates:

| Resource | Name | Purpose |
| --- | --- | --- |
| Deployment | `vllm-svc` | vLLM server pod (1 NVIDIA GPU) |
| Service | `vllm-svc` (port 8000) | In-cluster endpoint for the trainer |

The trainer connects to `http://vllm-svc.<namespace>.svc.cluster.local:8000/v1`.

## Prerequisites

1. **Shared PVC** — a PVC named `shared` in the target namespace, with the
   verifier model downloaded to `models/Qwen3-0.6B` on it (the notebooks'
   optional model download cells do this). The PVC is mounted at `/mnt` in the
   vLLM pod. The server must be in the **same namespace** and use the **same
   PVC** as the TrainJob — hidden states are written to the PVC and both the
   vLLM server and the training pod must see the same filesystem.
2. **GPU node** — at least 1 free NVIDIA GPU in the namespace's quota/region.
3. **Image pull access** — the pinned image requires a pull secret. Review the
   manifest's `imagePullSecrets` entry: adjust the secret name, or remove the
   block if your cluster can pull the image without a secret.
4. **Permissions** — deploying from a terminal requires a login with rights to
   create Deployments and Services in the namespace (the namespace owner has
   these). From a workbench notebook, the provided deploy cells log in with
   `NOTEBOOK_USER_TOKEN` for the same reason — the workbench pod's service
   account may lack these permissions.

## Deploy

From a terminal where you are logged in as the namespace owner (run from the
`offline/` or `data-only/` directory of the cloned repo):

```bash
oc apply -f ../manifests/vllm-server.yaml -n <your-namespace>
```

Alternatively, deploy without leaving the notebook: both the
[offline](../offline/speculator-offline-example.ipynb) and
[data-only](../data-only/speculator-data-only-example.ipynb) notebooks include
optional **Deploy the External vLLM Server** cells that log in with your user
token, apply the manifest, and wait for readiness.

## Verify Readiness

```bash
oc rollout status deployment/vllm-svc -n <your-namespace>
oc get pods -l app=vllm-svc -n <your-namespace>
```

Optionally, from the workbench terminal, confirm the API answers:

```bash
curl http://vllm-svc.<your-namespace>.svc.cluster.local:8000/health
```

> [!NOTE]
>
> **First start is slow:** the first deployment on a node must pull the large
> vLLM container image before the server can start — this alone can take up to
> 10 minutes. Later runs reuse the cached image and only need the model load
> time (a minute or two; the readiness probe allows 60s initially).

## Wire It Into a Notebook

The notebooks' Configuration cells default `VLLM_ENDPOINT` to
`http://vllm-svc.<namespace>.svc.cluster.local:8000/v1` (namespace detected from
the workbench pod), so deploying with the defaults requires no endpoint editing.

> [!IMPORTANT]
>
> `SPECULATOR_HS_PATH` in the manifest **must match** the `hidden_states_path`
> passed to the trainer. The manifest default matches the OFFLINE notebook.
> The data-only Method 2 deploy cell sets it on the deployed server via
> `oc set env` (derived from the notebook's `RUN_NAME`); when deploying from a
> terminal, set it yourself per the table below. The PVC `shared` root maps to
> `/mnt` in the vLLM pod.

| Notebook | `hidden_states_path` (notebook) | `SPECULATOR_HS_PATH` (manifest) |
| --- | --- | --- |
| OFFLINE (`RUN_NAME = "run-01"`) | `pvc://shared/speculator/run-01-offline/hidden_states` | `/mnt/speculator/run-01-offline/hidden_states` |
| DATA_ONLY Method 2 (`RUN_NAME = "run-01"`) | `pvc://shared/speculator/run-01/hidden_states` | `/mnt/speculator/run-01/hidden_states` |

If you change `RUN_NAME` in a notebook, update `SPECULATOR_HS_PATH` accordingly
(`/mnt/speculator/<RUN_NAME>[-offline]/hidden_states`) and re-apply the manifest.

## Customize

The manifest is driven by environment variables — edit them in the yaml and
re-apply:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SPECULATOR_VERIFIER_MODEL` | `/mnt/models/Qwen3-0.6B` | Verifier model path on the shared PVC. To train against a different model, download it to the PVC and point this at it. |
| `SPECULATOR_TARGET_LAYER_IDS` | `2, 14, 25, 28` | Eagle3 extraction layers. Must match `TARGET_LAYER_IDS` in the notebook — for a different verifier, follow its README guidance on choosing 4 layer IDs. |
| `SPECULATOR_HS_PATH` | `/mnt/speculator/run-01-offline/hidden_states` | Where hidden states are written. Must match the trainer's `hidden_states_path` (see table above). |
| `SPECULATOR_GPU_MEM_UTIL` | `0.9` | Fraction of GPU memory vLLM may use. Lower it if the pod OOMs during model load. |

> [!NOTE]
>
> The server runs on a **single GPU** — hidden state extraction does not
> currently support multi-GPU or tensor parallelism (the same limit as the
> SDK-managed vLLM sidecar), so the pod requests exactly one `nvidia.com/gpu`.

Changing the verifier model also means changing it in the notebook
(`VERIFIER_MODEL_PVC_URI` / `VERIFIER_MODEL`) and re-checking `target_layer_ids`.

## Cleanup

```bash
oc delete -f ../manifests/vllm-server.yaml -n <your-namespace>
```

The notebooks also include an optional cleanup cell. Deleting the server does
**not** remove the extracted hidden states or checkpoints on the PVC.

## Troubleshooting

Deployment-side failures:

- `Forbidden: ... cannot get resource "deployments"` when applying from a
  workbench — the pod's service account lacks permissions; the notebook's
  deploy cell logs in with `NOTEBOOK_USER_TOKEN` to run as your user.
  Deploying from a terminal where you are logged in as the namespace owner also
  works. Alternatively, an admin can grant the service account edit access:
  `oc adm policy add-role-to-user edit -z <service-account> -n <namespace>`
- Pod stuck in `ImagePullBackOff` — the pinned `quay.io/aipcc/rhaiis/cuda-ubi9`
  image needs a pull secret; check the manifest's `imagePullSecrets` entry
  exists in your namespace (`oc get secret aipcc-pull-secret -n <namespace>`)
- Pod stuck in `Pending` — no free GPU on the node
  (`oc describe pod -l app=vllm-svc -n <namespace>`)
- Pod not ready — check startup logs: `oc logs -l app=vllm-svc -n <namespace>`;
  remember the first deployment can spend up to 10 minutes pulling the image
- `MountVolume.SetUp failed` — the `shared` PVC does not exist in the
  namespace, or the model was not downloaded to `models/Qwen3-0.6B` on it
- Job-side failures (connection refused, wrong endpoint, empty hidden states)
  are covered in the [offline](../offline/README.md#troubleshooting) and
  [data-only](../data-only/README.md#troubleshooting) READMEs.
