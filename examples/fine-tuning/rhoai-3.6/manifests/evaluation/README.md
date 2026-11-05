# Run the Speculator Evaluation Job

This guide runs an evaluation sweep against a trained Eagle3 draft model. The Job
starts a temporary vLLM server with the verifier and draft model, runs the
Speculators evaluator, and saves results to a shared PVC.

You do **not** need to deploy the external vLLM server used for hidden-state
extraction in `DATA_ONLY` or `OFFLINE` training. The evaluation Job starts its
own temporary server.

Run the commands that reference the Job manifest or create the script ConfigMap
from this directory: `examples/fine-tuning/rhoai-3.6/manifests/evaluation/`.
The Python script is at `../../scripts/run_speculator_evaluation.py` relative to
this directory.

## Prerequisites

Before submitting the Job, confirm that:

- You can log in to the OpenShift cluster with the `oc` CLI.
- The namespace contains the shared PVC used by the workbench and training run.
  PVCs are namespace-scoped, so create the ConfigMap and Job in the namespace
  where that PVC exists.
- The PVC is `Bound` and contains:
  - The verifier model directory.
  - The trained draft checkpoint directory, such as
    `speculator/run-01/checkpoints/checkpoint_best`.
  - Space for evaluation output.
- The Job can request **one NVIDIA GPU**, 4 CPU cores and 32 GiB of memory
  (limits: 8 CPU cores and 64 GiB). Ask your administrator to confirm GPU
  availability and project quota.
- The cluster can pull the Job image from `registry.redhat.io`. Add an
  `imagePullSecrets` entry to the Job manifest if your cluster requires one.
- The Job can reach `raw.githubusercontent.com`, PyPI, and Hugging Face:
  the script downloads the pinned Speculators `v0.9.0` evaluator files,
  installs GuideLLM if needed, and downloads the default evaluation dataset.
  If your cluster has no outbound access, use approved internal mirrors or
  pre-populate these dependencies.

## Log in and select the namespace

Copy the `oc login` command from the OpenShift web console's **Copy login
command** page and run it in a terminal with the `oc` CLI:

```bash
oc login --token=<access-token> --server=https://api.<cluster-domain>:6443
```

Set the namespace and PVC name. Replace the example values with yours:

```bash
NAMESPACE="<your-namespace>"
PVC_NAME="shared"

oc whoami
oc project "$NAMESPACE"
oc get pvc "$PVC_NAME" -n "$NAMESPACE"
```

The PVC should show `Bound`. Confirm you have permission to create the resources
and read Job logs:

```bash
oc auth can-i create configmaps -n "$NAMESPACE"
oc auth can-i create jobs -n "$NAMESPACE"
oc auth can-i get pods -n "$NAMESPACE"
oc auth can-i get pods/log -n "$NAMESPACE"
oc get resourcequota -n "$NAMESPACE"
```

## Configure the script and Job manifest

Edit `USER_CONFIG` in
[`../../scripts/run_speculator_evaluation.py`](../../scripts/run_speculator_evaluation.py)
before creating the ConfigMap. The model and output paths are relative to the
PVC mount root; do not use `pvc://` URIs in these fields.

For example:

```python
"pvc_mount_root": "/mnt/persistent",
"verifier_model": "models/<verifier-model-directory>",
"draft_model": "speculator/<run-name>/checkpoints/checkpoint_best",
"output_dir": "speculator/<run-name>/evaluation",
"dataset": "RedHatAI/speculator_benchmarks",
"subsets": None,
```

Replace the verifier and draft paths with directories on your PVC. The output
directory is created by the script. The default dataset uses the `HumanEval`
subset. If you use another Hugging Face dataset, set `subsets` to a subset that
exists in that dataset. For a local JSONL dataset, set `dataset` to its absolute
path under `/mnt/persistent` and set `subsets` to `"local"`.

In `speculator-evaluation-job.yaml`:

- The manifest intentionally omits `metadata.namespace`, so the
  `-n "$NAMESPACE"` option selects the target namespace.
- Set `claimName` to the PVC name from the namespace. For example:

  ```yaml
  persistentVolumeClaim:
    claimName: shared
  ```

- Keep the PVC mount path at `/mnt/persistent` to match `pvc_mount_root` in the
  script.

The ConfigMap and Job must be created in the same namespace as the PVC. The
evaluation Job needs read access to the verifier and draft directories and
write access to the output directory.

## Create or update the script ConfigMap

From this directory, create the ConfigMap from the script under `scripts/`:

```bash
oc create configmap speculator-eval-script \
  --from-file=run_speculator_evaluation.py=../../scripts/run_speculator_evaluation.py \
  -n "$NAMESPACE" \
  --dry-run=client -o yaml |
  oc apply -n "$NAMESPACE" -f -
```

If you edit the script later, run this command again to update the ConfigMap.

## Submit and monitor the evaluation Job

If a previous Job with this name exists, delete it before starting a new run:

```bash
oc delete job speculator-evaluation -n "$NAMESPACE" --ignore-not-found
```

Apply the Job manifest:

```bash
oc apply -f speculator-evaluation-job.yaml -n "$NAMESPACE"
```

Watch the Job and its Pod:

```bash
oc get job speculator-evaluation -n "$NAMESPACE" -w
oc get pods -l app=speculator-evaluation -n "$NAMESPACE"
```

Follow the logs:

```bash
oc logs -f job/speculator-evaluation -n "$NAMESPACE"
```

The first run can take longer while the image is pulled, the evaluator files are
downloaded, and vLLM loads the models.

## Review the results

The script writes results under the configured `output_dir` on the PVC. For
example, if `output_dir` is `speculator/run-01/evaluation`, inspect that
directory from the workbench file browser.

The evaluation produces acceptance metrics and performance results, including
`acceptance.csv`, `perf_results.csv`, and raw evaluator output. Use the
acceptance results to see how often the verifier accepts draft tokens, and the
performance results to compare latency and throughput.

![Evaluation output files in the workbench](../../../images/evaluation-output-files.png)

## Clean up

Delete the Job and ConfigMap when you no longer need them:

```bash
oc delete job speculator-evaluation -n "$NAMESPACE" --ignore-not-found
oc delete configmap speculator-eval-script -n "$NAMESPACE" --ignore-not-found
```

This does not delete the verifier, draft checkpoint, or evaluation results on
the PVC.

## Troubleshooting

- **Job stays Pending:** Check GPU availability and namespace quota.
- **ImagePullBackOff:** Check registry access and the Job's `imagePullSecrets`.
- **Verifier or draft path not found:** Confirm the directories exist on the PVC
  and that the script paths are relative to `/mnt/persistent`.
- **Evaluation download or install fails:** Check egress to GitHub, PyPI, and
  Hugging Face, or configure approved internal mirrors.
- **Job fails on a second run:** Delete the previous Job before applying the
  manifest again; Jobs with the same name are not reusable after completion.
