# Progress Tracking with Kubeflow Trainer

This example demonstrates how to use real-time progress tracking in Kubeflow Trainer v2 on Red Hat OpenShift AI.

## Overview

Progress tracking provides visibility into your training jobs, including:

- Current step and epoch
- Training loss and metrics
- Estimated time remaining
- Throughput (samples/second)

When using RHAI trainers (`TransformersTrainer` or `TrainingHubTrainer`), progress tracking is **enabled by default** with no additional configuration required.

## Prerequisites

- Access to an OpenShift AI cluster with Kubeflow Trainer enabled
- A project (namespace) configured for training workloads
- Python 3.9+

## Quick Start

### 1. Install the SDK

```bash
pip install "kubeflow @ git+https://github.com/opendatahub-io/kubeflow-sdk.git@v0.2.1+rhai0"
```

### 2. Run the notebook

Open `progress-tracking-example.ipynb` in your workbench and execute the cells.

## Viewing Progress

### OpenShift AI Dashboard

1. Navigate to **Model training** in your project
2. Select your training job
3. View real-time metrics including steps, epochs, loss, and ETA

### CLI

```bash
# Get progress annotations
oc get trainjob <job-name> -o jsonpath='{.metadata.annotations.trainer\.opendatahub\.io/trainerStatus}' | jq .

# Watch job status
oc get trainjob <job-name> -w
```

### Example output

```json
{
  "progressPercentage": 75,
  "currentStep": 150,
  "totalSteps": 200,
  "currentEpoch": 1,
  "totalEpochs": 2,
  "estimatedRemainingSeconds": 45,
  "trainMetrics": {
    "loss": 0.023,
    "throughput_samples_sec": 58.2
  }
}
```

## How It Works

RHAI trainers automatically instrument your training code to:

1. Intercept HuggingFace Trainer callbacks
2. Report metrics to a sidecar metrics server
3. Write progress to TrainJob annotations

No code changes are required in your training function.

## Disabling Progress Tracking

If needed, you can disable progress tracking:

```python
trainer = TransformersTrainer(
    func=train_func,
    num_nodes=2,
    resources_per_node={"nvidia.com/gpu": 1},
    enable_progression_tracking=False,
)
```

## Files

| File | Description |
|------|-------------|
| `progress-tracking-example.ipynb` | Interactive notebook with step-by-step example |
| `README.md` | This file |

## Related Documentation

- [RHAI Trainers Guide](https://docs.redhat.com/en/documentation/red_hat_openshift_ai/)
- [Kubeflow SDK Repository](https://github.com/opendatahub-io/kubeflow-sdk)
