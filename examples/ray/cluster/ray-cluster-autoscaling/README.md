# Ray Cluster Autoscaling on Red Hat OpenShift AI

Demonstrate the full lifecycle of a Ray cluster with **in-tree autoscaling** on
Red Hat OpenShift AI (RHOAI): create the cluster, drive scale-up with a bursty
CPU workload, observe scale-down when idle, and tear the cluster down.

The notebook uses the CodeFlare SDK (`enable_autoscaling=True`, `min_workers`,
`max_workers`) and submits the companion script `autoscaling_load.py` through
the Ray Jobs API.

## Quick Links

| Section | Description |
| --- | --- |
| [Prerequisites](#prerequisites) | RHOAI version, Kueue constraints, RBAC |
| [Setup](#setup) | Workbench and repository setup |
| [Usage](#usage) | Running the lifecycle notebook |
| [Expected Outcomes](#expected-outcomes) | What success looks like |
| [Hardware Requirements](#hardware-requirements) | CPU-only smoke test sizing |
| [Related Examples](#related-examples) | Other Ray workloads on RHOAI |

## Overview

Ray in-tree autoscaling adjusts worker replica counts between `min_workers` and
`max_workers` based on pending task demand. This example focuses on **cluster
lifecycle and observability** on OpenShift AI — not on a specific ML workload.

Key technologies: **KubeRay**, **CodeFlare SDK**, **Ray Jobs API**.

> [!IMPORTANT]
> Ray cluster autoscaling is **not supported when Kueue manages your namespace**.
> Use a data science project without a default Kueue LocalQueue, or disable
> Kueue for the namespace before running this example. Elastic Ray jobs with
> Kueue are tracked in [RHAIRFE-909](https://redhat.atlassian.net/browse/RHAIRFE-909).
>
> [!NOTE]
> The [Docling batch processing example](../../data/docling/) patches
> `enableInTreeAutoscaling` on a **fixed-size** cluster for actor-pool scaling.
> This example uses SDK **`enable_autoscaling=True`** with `min_workers` /
> `max_workers` for true RayCluster worker replica autoscaling.

For a shorter SDK-focused walkthrough, see the
[CodeFlare SDK guided demo](https://github.com/project-codeflare/codeflare-sdk/tree/main/demo-notebooks/guided-demos/6_autoscaling.ipynb).

## Prerequisites

| Component | Minimum Version | Notes |
| --- | --- | --- |
| OpenShift | 4.14+ | Cluster-admin or namespace-admin access |
| RHOAI | 3.5+ | CodeFlare SDK with `enable_autoscaling` support |
| KubeRay | Bundled with RHOAI | RayCluster CRD must be available |
| Python | 3.11+ | Workbench runtime (3.12 in the default image) |

Additional requirements:

- The `codeflare`, `dashboard`, `ray`, and `workbenches` components enabled.
- A data science project namespace **without Kueue admission** for RayClusters.
- Sufficient worker node capacity for the head pod plus up to `max_workers`
  worker pods.

### RBAC Permissions

Your user or service account needs the following permissions in the project
namespace:

- `create`, `get`, `patch`, `delete` on `rayclusters.ray.io`
- `create`, `get`, `delete` on Ray job resources exposed through the dashboard
- `get`, `list` on `pods` — to observe worker scale events

### Workbench

| Setting | Value |
| --- | --- |
| Image | Minimal Python 3.12 (no GPU required) |
| Memory | 4–8 Gi |
| CPU | 2 cores |

## Setup

1. Open the **OpenShift AI** dashboard and create a data science project (or use
   an existing **non-Kueue** project).
2. Create a workbench with the settings above.
3. Clone this repository in the workbench:

   ```bash
   git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
   ```

4. Navigate to
   `red-hat-ai-examples/examples/ray/cluster/ray-cluster-autoscaling`.
5. Open `ray_cluster_autoscaling.ipynb`.
6. Set CodeFlare SDK authentication in the notebook (`TokenAuthentication` token
   and server from `oc whoami -t` and `oc whoami --show-server`).

If the workbench image does not include a recent CodeFlare SDK, run the `%pip
install` cell at the top of the notebook.

## Usage

Run the notebook top to bottom. It will:

1. Create a Ray cluster with `min_workers=1` and `max_workers=2`.
2. Wait until the cluster is ready and confirm one worker pod is running.
3. Submit `autoscaling_load.py`, which queues three single-CPU tasks (more than
   head + one worker can run concurrently).
4. Wait until a second worker pod appears (scale-up).
5. Wait for the job to finish and for worker count to return to `min_workers`
   (scale-down).
6. Delete the Ray job and call `cluster.down()`.

While the workload runs, use the Ray dashboard link from `cluster.details()` and
the `oc get raycluster` / `oc get pods` cells to watch replica counts change.

## Expected Outcomes

After a successful run you should see:

- `cluster.details()` reports the cluster in a ready state with a dashboard URL.
- Worker pod count starts at **1** (`min_workers`).
- While the load job runs, worker pod count increases to **2** (`max_workers`).
- After the job completes and the cluster idles, worker pod count returns to **1**.
- `cluster.down()` removes the RayCluster.

Typical timing on a small CPU cluster (default `LOAD_SLEEP_S=180`):

| Phase | Approximate duration |
| --- | --- |
| Cluster ready | 2–5 minutes |
| Scale-up observed | 1–5 minutes after job submit |
| Job completion | Depends on `LOAD_SLEEP_S` |
| Scale-down | Several minutes after job completion |

## Hardware Requirements

| Resource | Specification |
| --- | --- |
| **GPU** | Not required |
| **Head node** | 1 CPU, 8 Gi memory (defaults in notebook) |
| **Workers** | 1–2 pods × 1 CPU × 6 Gi memory each |
| **Cluster nodes** | Enough schedulable CPU/memory for head + 2 workers |

Adapt `ClusterConfiguration` CPU and memory requests if your cluster has tighter
capacity.

## Files

| File | Description |
| --- | --- |
| `ray_cluster_autoscaling.ipynb` | End-to-end autoscaling lifecycle notebook |
| `autoscaling_load.py` | Bursty CPU Ray job entrypoint |
| `example.yaml` | Example metadata (repo convention) |
| `pyproject.toml` | Pinned Python dependencies |

## Validation

This example has been validated with:

- OpenShift AI 3.5 development environment
- CPU-only Ray cluster (no GPU required)
- CodeFlare SDK with `enable_autoscaling` support

```python
ClusterConfiguration(
    name="ray-autoscale",
    enable_autoscaling=True,
    min_workers=1,
    max_workers=2,
    head_cpu_requests=1,
    head_cpu_limits=1,
    head_memory_requests=7,
    head_memory_limits=8,
    worker_cpu_requests=1,
    worker_cpu_limits=1,
    worker_memory_requests=5,
    worker_memory_limits=6,
    head_extended_resource_requests={"nvidia.com/gpu": 0},
    worker_extended_resource_requests={"nvidia.com/gpu": 0},
)
```

Load job entrypoint:

```text
AUTOSCALING_TASKS=3 AUTOSCALING_TASK_SLEEP_S=180 python autoscaling_load.py
```

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| SDK error when creating cluster with autoscaling | Kueue manages the namespace | Use a non-Kueue project; see RHAIRFE-909 |
| Cluster never reaches ready | Insufficient node capacity | Reduce memory/CPU requests or add worker nodes |
| Scale-up not observed | Load job failed or finished too quickly | Check job logs; increase `LOAD_SLEEP_S` |
| `cluster.job_client` fails | Dashboard route not ready | Re-run `cluster.wait_ready()` and `cluster.details()` |
| Scale-down takes a long time | Normal autoscaler idle delay | Wait several minutes after job completion |

## Related Examples

- [Distributed PDF processing with Ray Data and Docling](../../data/docling/) —
  RayCluster + job submission pattern on RHOAI
- [RAG ingestion with Ray Data](../../data/rag/ray-data-pipeline/) — longer-lived
  RayCluster workloads
- [CodeFlare SDK autoscaling guided demo](https://github.com/project-codeflare/codeflare-sdk/tree/main/demo-notebooks/guided-demos/6_autoscaling.ipynb) —
  SDK-focused walkthrough
