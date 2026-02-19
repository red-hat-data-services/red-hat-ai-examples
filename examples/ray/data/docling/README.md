# Distributed PDF Processing with Ray Data and Docling

This example demonstrates how to build and submit a distributed PDF-to-JSON conversion pipeline using [Ray Data](https://docs.ray.io/en/latest/data/data.html) and [Docling](https://github.com/DS4SD/docling) on Red Hat OpenShift AI. The pipeline is submitted as a **RayJob** via the CodeFlare SDK, which handles cluster lifecycle and job management.

## Overview

The notebook (`ray-data-with-docling.ipynb`) walks through:

1. Authenticating to an OpenShift cluster
2. Creating a Ray Data processing script that converts PDFs to structured JSON using Docling
3. Configuring a RayJob with a managed RayCluster (including PVC mounts, resource requests, and performance tuning parameters)
4. Submitting the job and monitoring its status
5. Retrieving job logs with a detailed performance report

### Pipeline architecture

The submitted script (`ray_data_process_async.py`) uses a stateful `DoclingProcessor` actor pool to:

- **Read** PDF files from a Persistent Volume Claim (PVC) using `ray.data.read_binary_files`
- **Convert** PDFs to structured JSON using Docling's `DocumentConverter` with configurable pipeline options (OCR, table structure extraction)
- **Write** results back to the PVC with retry logic

Key optimizations:

| Optimization | Description |
| --- | --- |
| One-time model loading | Docling models are loaded once per actor, avoiding repeated startup overhead |
| Actor pool autoscaling | `ActorPoolStrategy` with configurable `min_size`/`max_size` |
| Streaming execution | Read, process, and write stages overlap via `iter_batches()` with prefetching |
| Configurable parallelism | `MIN_ACTORS`, `MAX_ACTORS`, `CPUS_PER_ACTOR`, and `BATCH_SIZE` are all tunable via environment variables |

## Requirements

### OpenShift AI cluster

- Red Hat OpenShift AI with:
  - KubeRay operator installed

### Hardware requirements

#### RayCluster (managed by the RayJob)

| Component | Configuration | Notes |
| --- | --- | --- |
| Worker nodes | 8 nodes x 8 CPUs | Configurable in notebook |
| Worker memory | 8Gi per worker | Adjust based on PDF complexity |
| Head node | Default resources | Manages scheduling only |

#### Workbench

| Image | GPU | CPU | Memory | Notes |
| --- | --- | --- | --- | --- |
| Minimal Python 3.12 | None | 2 cores | 8Gi | Used to submit jobs only |

### Storage

| Purpose | Size | Access mode | Notes |
| --- | --- | --- | --- |
| Shared PVC | Varies by dataset | ReadWriteMany (RWX) | Required for concurrent reads/writes from all workers |

> [!NOTE]
> The PVC must use `ReadWriteMany` (RWX) access mode so that all Ray worker pods can read input PDFs and write output files concurrently.

## Performance tuning parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `NUM_FILES` | 5000 | Number of PDF files to process |
| `MIN_ACTORS` | 16 | Minimum warm actors (avoids cold starts) |
| `MAX_ACTORS` | 16 | Maximum parallel actors |
| `CPUS_PER_ACTOR` | 4 | CPUs allocated to each Docling actor |
| `BATCH_SIZE` | 1 | PDFs per actor batch (1 for large PDFs, 2-4 for small PDFs) |

**Sizing formula:** `MAX_ACTORS = total_worker_cpus / CPUS_PER_ACTOR`

For example, 8 workers x 8 CPUs = 64 total CPUs, so `MAX_ACTORS = 16` with `CPUS_PER_ACTOR = 4`.

## Setup

### 1. Access OpenShift AI Dashboard

Access the OpenShift AI dashboard from the top navigation bar menu.

### 2. Create a Data Science Project

Log in, then go to **Data Science Projects** and create a project.

### 3. Create a PVC with RWX Access

Create a PersistentVolumeClaim with `ReadWriteMany` access mode and upload your PDF files to it:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-rwx-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
```

### 4. Create a Workbench

Create a workbench with a Minimal Python 3.12 image. No GPU is required since the workbench is only used to submit the RayJob.

### 5. Clone the Repository

From your workbench, clone this repository:

```bash
git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
```

Navigate to `examples/ray/data/docling` and open the `ray-data-with-docling.ipynb` notebook.

## Running the example

The notebook walks you through:

1. **Importing SDK components** -- CodeFlare SDK (`RayJob`, `ManagedClusterConfig`) and Kubernetes client
2. **Authenticating** -- `oc login` to your OpenShift cluster
3. **Creating the processing script** -- Writes `ray_data_process_async.py` with the Docling actor pool
4. **Verifying the PVC** -- Checks that the PVC exists and has RWX access mode
5. **Configuring the RayJob** -- Sets up cluster specs, PVC mounts, environment variables, and runtime dependencies
6. **Submitting the job** -- Submits the RayJob to KubeRay
7. **Monitoring status** -- Checks job status via the CodeFlare SDK
8. **Retrieving logs** -- Views job logs including a detailed performance report with throughput metrics, actor distribution, and error summary

## Customization

| Parameter | Where to change | Description |
| --- | --- | --- |
| `num_workers` | `ManagedClusterConfig` | Number of Ray worker nodes |
| `worker_cpu_requests` | `ManagedClusterConfig` | CPUs per worker node |
| `worker_memory_requests` | `ManagedClusterConfig` | Memory per worker node |
| `image` | `ManagedClusterConfig` | Container image with Ray and Docling |
| `INPUT_PATH` | Environment variables | Path to input PDFs on the PVC |
| `OUTPUT_PATH` | Environment variables | Path for output JSON files on the PVC |
| `active_deadline_seconds` | `RayJob` | Job timeout (default: 7200s / 2 hours) |

## Troubleshooting

### Job not starting

```bash
# Check RayJob status
oc get rayjob <job-name> -o yaml

# Check for pending pods
oc get pods -l ray.io/cluster=<cluster-name>
```

### PVC access issues

Verify the PVC has `ReadWriteMany` access mode:

```bash
oc get pvc <pvc-name> -o jsonpath='{.spec.accessModes}'
```

### Viewing job logs

```bash
# Find the head pod
oc get pods -l ray.io/node-type=head -o name

# Stream job logs
oc exec -it <head-pod> -- ray job logs -f <submission-id>
```

### Actor errors

Check the performance report in the job logs for error details. Common issues:

- **File empty or too small** -- Corrupted or incomplete PDF files
- **Timeout errors** -- Increase `active_deadline_seconds` or reduce `NUM_FILES`
- **Memory errors** -- Reduce `MAX_ACTORS` or increase worker memory
