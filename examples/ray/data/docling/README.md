# Distributed PDF Processing with Ray Data and Docling

This example demonstrates how to build and run a distributed PDF-to-JSON conversion pipeline using [Ray Data](https://docs.ray.io/en/latest/data/data.html) and [Docling](https://github.com/DS4SD/docling) on Red Hat OpenShift AI. Two notebooks are provided, each using a different approach to cluster and job management via the [CodeFlare SDK](https://github.com/project-codeflare/codeflare-sdk).

## Notebooks

| Notebook | Approach | Use case |
|---|---|---|
| `ray-data-with-docling.ipynb` | **RayJob** with managed cluster | Single batch jobs with automatic cluster lifecycle |
| `ray-cluster-data-with-docling.ipynb` | **RayCluster** with job submission | Long-lived clusters for submitting multiple jobs |

### RayJob approach (`ray-data-with-docling.ipynb`)

Uses the CodeFlare SDK `RayJob` and `ManagedClusterConfig` to submit a job that automatically creates a RayCluster, runs the processing pipeline, and tears down the cluster when done. This is ideal for one-off batch processing where you don't need to manage cluster lifecycle.

### RayCluster approach (`ray-cluster-data-with-docling.ipynb`)

Uses the CodeFlare SDK `Cluster` and `ClusterConfiguration` to create a persistent RayCluster, then submits jobs to it using the Ray Job Submission Client. This is ideal for interactive or iterative workflows where you want to submit multiple jobs to the same cluster.

## Architecture

Both notebooks submit the same processing script (`ray_data_process_async.py`), which implements a three-stage Ray Data pipeline distributed across a RayCluster.

### Cluster architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       OpenShift / Kubernetes                         │
│                                                                      │
│  ┌────────────────────┐                                              │
│  │   KubeRay Operator  │  Manages RayCluster lifecycle               │
│  └─────────┬──────────┘                                              │
│            │ creates                                                  │
│            ▼                                                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                         RayCluster                              │  │
│  │                                                                  │  │
│  │  ┌──────────────────┐                                            │  │
│  │  │    Head Node       │  Schedules Ray Data stages               │  │
│  │  └────────┬─────────┘                                            │  │
│  │           │                                                       │  │
│  │     ┌─────┼──────┬──────────┬─── ─ ─ ─ ┐                        │  │
│  │     ▼     ▼      ▼          ▼           ▼                        │  │
│  │  ┌──────┐┌──────┐┌──────┐┌──────┐   ┌──────┐                   │  │
│  │  │Wkr 1 ││Wkr 2 ││Wkr 3 ││Wkr 4 │   │Wkr N │                   │  │
│  │  │      ││      ││      ││      │   │      │                   │  │
│  │  │Doclng││Doclng││Doclng││Doclng│   │Doclng│                   │  │
│  │  │Actor ││Actor ││Actor ││Actor │   │Actor │                   │  │
│  │  └──┬───┘└──┬───┘└──┬───┘└──┬───┘   └──┬───┘                   │  │
│  │     │       │       │       │           │                        │  │
│  └─────┼───────┼───────┼───────┼───────────┼────────────────────────┘  │
│        │       │       │       │           │                           │
│        ▼       ▼       ▼       ▼           ▼                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    PVC (ReadWriteMany)                          │  │
│  │                                                                  │  │
│  │   input/pdfs/  ──────────────────────►  output/json/            │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Ray Data pipeline stages

The processing script (`ray_data_process_async.py`) runs the following pipeline:

```
┌──────────────────┐     ┌───────────────────────────┐     ┌──────────────────┐
│   Stage 1: Read   │     │   Stage 2: Process         │     │  Stage 3: Report  │
│                    │────▶│                             │────▶│                    │
│ ray.data.read_     │     │ DoclingProcessor actors     │     │ iter_batches()     │
│ binary_files()     │     │                             │     │                    │
│                    │     │ For each PDF:               │     │ Collects results   │
│ Reads PDFs from    │     │  1. Convert via Docling     │     │ and prints a       │
│ PVC into Ray       │     │  2. Export to JSON dict     │     │ performance        │
│ data blocks        │     │  3. Write JSON to PVC       │     │ report with:       │
│                    │     │                             │     │  - Throughput       │
│ .filter(.pdf)      │     │ ActorPoolStrategy:          │     │  - Actor stats     │
│ .limit(NUM_FILES)  │     │  min_size -> max_size       │     │  - Error summary   │
└──────────────────┘     └───────────────────────────┘     └──────────────────┘
                                │
                          Prefetching and streaming
                          overlap all three stages
```

### Key optimizations

| Optimization | Description |
|---|---|
| One-time model loading | Docling models are loaded once per actor, avoiding repeated startup overhead |
| Actor pool autoscaling | `ActorPoolStrategy` with configurable `min_size`/`max_size` |
| Streaming execution | Read, process, and write stages overlap via `iter_batches()` with prefetching |
| Configurable parallelism | `MIN_ACTORS`, `MAX_ACTORS`, `CPUS_PER_ACTOR`, and `BATCH_SIZE` are all tunable via environment variables |

## Requirements

### OpenShift AI cluster

- Red Hat OpenShift AI with:
  - KubeRay operator installed

### Hardware requirements

#### RayCluster

| Component | Configuration | Notes |
|---|---|---|
| Worker nodes | 8 nodes x 8 CPUs | Configurable in notebook |
| Worker memory | 8Gi per worker | Adjust based on PDF complexity |
| Head node | Default resources | Manages scheduling only |

#### Workbench

| Image | GPU | CPU | Memory | Notes |
|---|---|---|---|---|
| Minimal Python 3.12 | None | 2 cores | 8Gi | Used to submit jobs only |

### Storage

| Purpose | Size | Access mode | Notes |
|---|---|---|---|
| Shared PVC | Varies by dataset | ReadWriteMany (RWX) | Required for concurrent reads/writes from all workers |

> [!NOTE]
> The PVC must use `ReadWriteMany` (RWX) access mode so that all Ray worker pods can read input PDFs and write output files concurrently.

## Performance tuning parameters

Both notebooks use the same tuning parameters, configured as environment variables in the job submission:

| Parameter | Default | Description |
|---|---|---|
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

### 3. Create a PVC with RWX access

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

### 4. Create a workbench

Create a workbench with a Minimal Python 3.12 image. No GPU is required since the workbench is only used to submit jobs.

### 5. Clone the repository

From your workbench, clone this repository:

```bash
git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
```

Navigate to `examples/ray/data/docling` and open the notebook for your chosen approach.

## Running the examples

### RayJob approach (`ray-data-with-docling.ipynb`)

1. **Import SDK components** -- CodeFlare SDK (`RayJob`, `ManagedClusterConfig`) and Kubernetes client
2. **Authenticate** -- `oc login` to your OpenShift cluster
3. **Create the processing script** -- Writes `ray_data_process_async.py` with the Docling actor pool
4. **Verify the PVC** -- Checks that the PVC exists and has RWX access mode
5. **Configure the RayJob** -- Sets up managed cluster specs, PVC mounts, environment variables, and runtime dependencies
6. **Submit the job** -- Creates a RayJob custom resource that manages the full cluster lifecycle
7. **Monitor status** -- Checks job status via the CodeFlare SDK
8. **Retrieve logs** -- Views job logs including a detailed performance report

### RayCluster approach (`ray-cluster-data-with-docling.ipynb`)

1. **Import SDK components** -- CodeFlare SDK (`Cluster`, `ClusterConfiguration`) and Kubernetes client
2. **Authenticate** -- `oc login` to your OpenShift cluster
3. **Create the processing script** -- Writes `ray_data_process_async.py` with the Docling actor pool
4. **Verify the PVC** -- Checks that the PVC exists and has RWX access mode
5. **Create a RayCluster** -- Defines cluster resources and creates the cluster
6. **Submit a job** -- Uses the Ray Job Submission Client to submit the processing job
7. **Monitor status** -- Lists and checks job status via the job client
8. **Retrieve logs** -- Views or streams job logs
9. **Clean up** -- Deletes the job and tears down the cluster

## Customization

| Parameter | Where to change | Description |
|---|---|---|
| `num_workers` | Cluster configuration | Number of Ray worker nodes |
| `worker_cpu_requests` | Cluster configuration | CPUs per worker node |
| `worker_memory_requests` | Cluster configuration | Memory per worker node |
| `image` | Cluster configuration | Container image with Ray and Docling |
| `INPUT_PATH` | Environment variables | Path to input PDFs on the PVC |
| `OUTPUT_PATH` | Environment variables | Path for output JSON files on the PVC |
| `active_deadline_seconds` | `RayJob` (RayJob approach only) | Job timeout (default: 7200s / 2 hours) |

## Troubleshooting

### Job not starting

```bash
# Check RayJob status
oc get rayjob <job-name> -o yaml

# Check RayCluster status
oc get raycluster <cluster-name> -o yaml

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
