# Serve a Speculator Model

This guide deploys a vLLM `ServingRuntime` and KServe `InferenceService` for
inference with a verifier model and its trained draft model. Reuse
`model-serving.yaml` for the eight model configurations by updating the small
set of model settings below.

Run commands that reference `model-serving.yaml` from this directory:
`examples/fine-tuning/rhoai-3.6/speculator/manifests/serving/`.

## Prerequisites

Before deploying, confirm that:

- OpenShift AI Model Serving and KServe are enabled.
- The target namespace contains the shared PVC used by the workbench and
  training run.
- The PVC is `Bound` and contains the verifier model and draft checkpoint.
  It needs read-write-many access if the workbench and serving Pod mount it at
  the same time.
- The namespace has quota and an available NVIDIA GPU. The example requests
  one GPU, 4 CPU cores and 32 GiB of memory (limits: 8 CPU cores and 64 GiB).
- The cluster can pull the pinned vLLM image.
- You can create KServe `ServingRuntime` and `InferenceService` resources in
  the namespace.

The manifest enables Hugging Face offline mode. The model files must already
be on the PVC.

## Log in and select the namespace

Copy the `oc login` command from the OpenShift web console's **Copy login
command** page and run it in a terminal with the `oc` CLI:

```bash
oc login --token=<access-token> --server=https://api.<cluster-domain>:6443
```

Set the namespace containing the PVC:

```bash
NAMESPACE="<your-namespace>"

oc whoami
oc project "$NAMESPACE"
oc get pvc shared -n "$NAMESPACE"
oc get resourcequota -n "$NAMESPACE"
```

The PVC should show `Bound`. The InferenceService and PVC must be in the same
namespace.

Check that you can create the KServe resources:

```bash
oc auth can-i create servingruntimes.serving.kserve.io -n "$NAMESPACE"
oc auth can-i create inferenceservices.serving.kserve.io -n "$NAMESPACE"
```

## Configure the model

Update these settings in the `env` section of the `ServingRuntime`:

- `SPECULATOR_VERIFIER_MODEL` — verifier model path. The example uses
  `/mnt/models/models/Qwen3-0.6B`; replace it if you use a different verifier.
- `MAX_MODEL_LEN` — maximum context length in tokens. Keep it at or below the
  verifier model's supported context length; the default is `40960`.
- `SPECULATIVE_CONFIG` — vLLM JSON containing the speculative-decoding method,
  draft model path, and method-specific settings.
- `SERVED_MODEL_NAME` — model name clients use in requests.
- `SPECULATOR_GPU_MEM_UTIL` — optional GPU memory tuning.

For example:

```yaml
- name: SPECULATOR_VERIFIER_MODEL
  value: /mnt/models/models/Qwen3-0.6B
- name: MAX_MODEL_LEN
  value: "40960"
- name: SPECULATIVE_CONFIG
  value: '{"method":"eagle3","model":"/mnt/models/speculator/run-01/checkpoints/checkpoint_best","draft_tensor_parallel_size":1,"num_speculative_tokens":5}'
- name: SERVED_MODEL_NAME
  value: speculator-model
- name: SPECULATOR_GPU_MEM_UTIL
  value: "0.9"
```

The KServe runtime expands these values in its container arguments. The other
runtime settings, including the vLLM image and CPU, memory, and GPU requests,
are shared defaults. Change them only if your model or cluster requires it.

The manifest sets `storageUri: pvc://shared`. KServe mounts that PVC at
`/mnt/models`. In this example, the PVC contains:

```text
models/Qwen3-0.6B/
speculator/run-01/checkpoints/checkpoint_best/
```

Therefore, the verifier path in the container is
`/mnt/models/models/Qwen3-0.6B`: the first `models` is KServe's mount path, and
the second is the directory on the PVC. If you use a different PVC name, update
`storageUri`.

To use a shorter verifier path, place the verifier in a directory such as
`verifier/Qwen3-0.6B` on the PVC and set `SPECULATOR_VERIFIER_MODEL` to
`/mnt/models/verifier/Qwen3-0.6B`. Keep the KServe mount prefix `/mnt/models`.

## Deploy and verify

The manifest omits `metadata.namespace`, so pass the namespace with `-n`:

```bash
oc apply -f model-serving.yaml -n "$NAMESPACE"
```

Wait for the InferenceService to become ready:

```bash
oc get inferenceservice model-serving -n "$NAMESPACE" -w
```

Check the runtime and predictor Pod:

```bash
oc get servingruntime model-serving-runtime -n "$NAMESPACE"
oc get pods -l serving.kserve.io/inferenceservice=model-serving -n "$NAMESPACE"
```

The first startup can take several minutes while the image is pulled and vLLM
loads the models. To inspect the predictor logs:

```bash
POD=$(oc get pods \
  -l serving.kserve.io/inferenceservice=model-serving \
  -n "$NAMESPACE" \
  -o jsonpath='{.items[0].metadata.name}')

oc logs "$POD" -c kserve-container -n "$NAMESPACE"
```

## Test the endpoint

Choose one of these options. The InferenceService URL is cluster-local and
cannot be resolved directly from your Mac.

### Option 1: Run from inside the cluster

From a workbench or another Pod that can reach the endpoint, get the internal
address from `status.address.url`:

```bash
MODEL_URL=$(oc get inferenceservice model-serving \
  -n "$NAMESPACE" \
  -o jsonpath='{.status.address.url}')

echo "$MODEL_URL"
curl -fsS "$MODEL_URL/v1/models"
```

If you are in a shell inside the predictor container (for example, a K9s
container shell), `oc` might not be installed. Test the server directly on its
container port instead:

```bash
MODEL_URL="http://localhost:8080"
curl -fsS "$MODEL_URL/v1/models"
```

Use the same `MODEL_URL` for a test chat-completion request:

```bash
curl -fsS "${MODEL_URL%/}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "speculator-model",
    "messages": [
      {"role": "user", "content": "Explain speculative decoding in one sentence."}
    ],
    "max_tokens": 64
  }'
```

### Option 2: Port-forward from your local machine

On your local machine, find the predictor Pod and start a port-forward:

```bash
POD=$(oc get pods \
  -l serving.kserve.io/inferenceservice=model-serving \
  -n "$NAMESPACE" \
  -o jsonpath='{.items[0].metadata.name}')

oc port-forward -n "$NAMESPACE" "pod/$POD" 8080:8080
```

Keep this command running while you send requests. In another terminal, set
`MODEL_URL` to localhost and check the endpoint:

```bash
MODEL_URL="http://localhost:8080"
curl -fsS "$MODEL_URL/v1/models"
```

Send the same chat-completion request through the port-forward:

```bash
curl -fsS "${MODEL_URL%/}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "speculator-model",
    "messages": [
      {"role": "user", "content": "Explain speculative decoding in one sentence."}
    ],
    "max_tokens": 64
  }'
```

For clients outside the cluster without port-forwarding, configure an approved
route and access policy separately.

## Clean up

Delete the InferenceService first, then the ServingRuntime:

```bash
oc delete inferenceservice model-serving -n "$NAMESPACE"
oc delete servingruntime model-serving-runtime -n "$NAMESPACE"
```

This does not delete the verifier, draft checkpoint, or other files on the PVC.
