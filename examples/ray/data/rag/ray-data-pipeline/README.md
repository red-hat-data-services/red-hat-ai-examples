# RAG Ingestion with Ray Data, Docling, and vLLM

Build a distributed RAG ingestion pipeline on Red Hat OpenShift AI.
Parse PDFs with Docling, generate embeddings with vLLM (via Ray Data's
`vLLMEngineProcessorConfig`), and store vectors in Milvus — all running
as a RayJob on an existing RayCluster.

## Overview

This example demonstrates a production-style RAG ingestion workflow using
Ray Data's streaming execution engine. Three pipeline stages run in parallel
on a heterogeneous RayCluster (CPU + GPU workers), processing PDFs end-to-end
from raw files to searchable vector embeddings in Milvus.

Key technologies: **Ray Data**, **Docling** (PDF parsing + chunking),
**vLLM** (GPU-accelerated embedding), **Milvus** (vector database),
**CodeFlare SDK** (RayJob submission).

## Architecture

```mermaid
flowchart TB
  subgraph Ingest["Ingestion — RayJob via rag_ingestion.ipynb"]
    direction TB
    PVC[("PVC — PDFs")]
    S1["1 — DoclingChunkActor: parse + chunk (CPU)"]
    S2["2 — vLLM embedding processor (GPU)"]
    S3["3 — MilvusWriteActor: batch insert"]
    MV[("Milvus")]
    PVC --> S1 --> S2 --> S3 --> MV
  end

  subgraph Query["Query (optional) — rag_query.ipynb"]
    direction TB
    Q["User question"]
    EQ["Embed question"]
    SRCH["Vector search — top-k"]
    CTX["Context from chunks"]
    LLM["vLLM — OpenAI-compatible"]
    Q --> EQ --> SRCH --> CTX --> LLM
  end

  MV -.->|rag_documents| SRCH
```

<details>
<summary>Diagram not rendering? View as image.</summary>

![RAG Architecture](assets/rag-architecture.png)
</details>

Ray Data **streams** the three ingestion stages so they overlap — Docling
(the slowest) does not block embedding from starting on completed chunks.

## Prerequisites

### Cluster

- **Red Hat OpenShift AI** with the **KubeRay operator** installed
- An existing **RayCluster** with CPU and GPU workers
  (see `manifests/raycluster-rag-optimized.yaml`)
- **Milvus** accessible from the Ray cluster (standalone or operator-managed)

> [!NOTE]
> If Milvus runs in a different namespace from the RayCluster, a
> `NetworkPolicy` (or namespace label) must allow traffic from the Ray
> namespace to the Milvus service port. Without this the pipeline will
> silently hang at the Milvus connection step.

### Runtime image

The RayCluster manifest and RayJob must use a container image that includes
Ray 2.54+, Docling, vLLM, and pymilvus. A ready-to-build Dockerfile is
available in the
[distributed-workloads](https://github.com/opendatahub-io/distributed-workloads/tree/main/images/runtime/examples/ray-data-rag)
repository:

```bash
cd images/runtime/examples/ray-data-rag
podman build -t quay.io/<you>/ray-data-rag:latest -f Dockerfile .
podman push quay.io/<you>/ray-data-rag:latest
```

Then update the `image:` fields in `manifests/raycluster-rag-optimized.yaml`
to point to your pushed image before applying.

### Storage

- A **ReadWriteMany (RWX)** PVC mounted on all Ray workers and the head node
- Input PDFs uploaded to the PVC (e.g. under `/mnt/data/input/pdfs`)

### Workbench

| Setting | Value |
| ------- | ----- |
| Image | Minimal Python 3.12 (no GPU required) |
| Memory | 4–8 Gi |
| CPU | 2 cores |

The workbench only submits the RayJob — all heavy processing happens on
the RayCluster.

## Hardware Requirements

| Resource | Specification |
| -------- | ---------------- |
| **GPU** | 1× NVIDIA T4 (16 GB) or A10G (24 GB) |
| **CPU workers** | 8 nodes × 4 CPUs × 16 Gi memory |
| **Head node** | 2 CPUs, 10 Gi memory |
| **Storage** | 50 Gi RWX PVC |
| **Milvus** | Standalone or operator-managed |

> [!NOTE]
> The RayCluster manifest (`manifests/raycluster-rag-optimized.yaml`) is
> sized for 8 CPU workers + 1 GPU worker. Scale worker counts up or down
> by editing `replicas` and adjusting `NUM_ACTORS` / `CPUS_PER_ACTOR` in
> the notebook to match.

## Files

| File | Description |
| ---- | ----------- |
| `rag_ingestion.ipynb` | Main notebook — configure, review pipeline, submit RayJob |
| `docling_milvus_process.py` | RayJob entrypoint (3-stage Ray Data pipeline) |
| `manifests/raycluster-rag-optimized.yaml` | RayCluster spec (CPU + GPU workers) |
| `rag_query.ipynb` | Optional query notebook — without-RAG vs with-RAG comparison |
| `rag_helpers.py` | Query-side helpers (keeps notebook cells short) |
| `fetch_sample_pdfs.sh` | Download all 1000 PDFs from the [Open RAG Benchmark](https://huggingface.co/datasets/deepmatics/open_ragbench) dataset |
| `.env.example` | Template for environment variables |

## Setup

1. **Build and push the runtime image** following the instructions in
   [Runtime image](#runtime-image) above.

2. **Update the RayCluster image** in `manifests/raycluster-rag-optimized.yaml`
   with your container image, then apply:

   ```bash
   oc apply -f manifests/raycluster-rag-optimized.yaml -n <namespace>
   ```

3. **Upload PDFs** to the RWX PVC. To download the full
   [Open RAG Benchmark](https://huggingface.co/datasets/deepmatics/open_ragbench)
   dataset (1000 arXiv PDFs, ~743 MB):

   ```bash
   ./fetch_sample_pdfs.sh
   oc cp sample_pdfs/ <head-pod>:/mnt/data/input/pdfs -n <namespace>
   ```

   Set `NUM_FILES` in the notebook to limit how many PDFs to process
   (0 = all).

## Usage

1. **Open `rag_ingestion.ipynb`** in your RHOAI workbench and run cells
   top-to-bottom:
   - Authenticate (`oc login`)
   - Configure cluster, PVC, Milvus, and vLLM embedding settings
   - Review the pipeline overview
   - Submit the RayJob
   - Monitor status and fetch logs

2. **Verify** the Milvus collection is populated (row count is printed in
   the job logs performance report and in the notebook's Verify cell).

3. **(Optional)** Open `rag_query.ipynb` to test retrieval quality — compare
   LLM answers without RAG vs with RAG.

## Expected Outcomes

After a successful ingestion run you should see:

- **Performance report** in the RayJob logs showing documents processed,
  total chunks, wall-clock time, throughput (chunks/sec, docs/sec), and
  per-stage timing breakdown (Docling parse, chunking, embedding, Milvus write).
- **Milvus row count** matching the total chunks reported — e.g. ~120,000
  vectors for 1000 PDFs at `CHUNK_MAX_TOKENS=256`.
- **`rag_query.ipynb`** returns cited answers from the ingested papers when
  queried with RAG, compared to generic/incorrect answers without RAG.

Typical performance on the reference hardware (8 CPU workers + 1 T4 GPU):

| Workload | Wall clock | Throughput |
| -------- | ---------- | ---------- |
| 50 PDFs | ~8 minutes | ~21 chunks/sec |
| 1000 PDFs | ~2.5 hours | ~21 chunks/sec |

## Configuration

All parameters are environment variables set in the ingestion notebook.

| Parameter | Default | Description |
| --------- | ------- | ----------- |
| `VLLM_MODEL_SOURCE` | `intfloat/multilingual-e5-large` | Embedding model for vLLM |
| `VLLM_BATCH_SIZE` | 4 | Batch size for embedding processor. Higher values increase throughput but require more GPU memory; reduce to 1–2 on T4 (16 GB) if OOM occurs. |
| `VLLM_CONCURRENCY` | 1 | GPU workers for embedding |
| `VLLM_ENGINE_KWARGS_JSON` | `{}` | vLLM engine args (JSON); set for your GPU |
| `EMBEDDING_DIM` | 1024 | Vector dimension (must match model) |
| `NUM_ACTORS` | 6 | Docling parsing actors (CPU-heavy). Too many actors vs total CPUs can stall streaming — see [Sizing for your hardware](#sizing-for-your-hardware). |
| `CPUS_PER_ACTOR` | 4 | CPUs per Docling actor |
| `NUM_MILVUS_ACTORS` | 2 | Milvus write actors (I/O-bound) |
| `NUM_FILES` | 0 | PDFs to process (0 = all) |
| `BATCH_SIZE` | 2 | PDFs per Docling actor batch |
| `REPARTITION_FACTOR` | 2 | Multiplier applied when repartitioning before embedding. Higher spreads blocks across the cluster (can smooth hotspots) but increases shuffle cost; tune with dataset size and CPU budget. |
| `CHUNK_MAX_TOKENS` | 256 | Max tokens per chunk |
| `MILVUS_BATCH_SIZE` | 64 | Vectors per Milvus insert batch |

### Sizing for your hardware

Ray Data runs Docling (`NUM_ACTORS` CPU actors), vLLM on GPU, and Milvus writers at the same time. **Actor-based CPU stages are sensitive to how much of the cluster you reserve for Docling:** if those actors claim too large a share of total CPUs, the streaming executor can stall waiting for capacity — often mistaken for a deadlock unless you leave enough headroom for Ray, Milvus actors, GPU-worker CPUs, and the head node.

**70% rule:** Aim to use at most about **70%** of **total cluster CPUs** for Docling (`NUM_ACTORS × CPUS_PER_ACTOR`), and leave roughly **30%** for scheduling, Milvus write actors, GPU-worker CPUs, object store, and other overhead.

Use this as a **starting point** for `NUM_ACTORS`:

```text
max_actors = floor(total_cluster_cpus × 0.70 / CPUS_PER_ACTOR)
```

Example clusters with `CPUS_PER_ACTOR = 4` (total CPUs include worker pools plus typical head/GPU-worker CPU contributions as in the table labels):

| Cluster | Total CPUs | 70% CPU budget | max NUM_ACTORS (formula) |
| ------- | ----------- | -------------- | ------------------------ |
| Small (4 workers × 4 CPU + head 2 CPU) | 18 | 12 | 3 |
| Reference (8 workers × 4 CPU + 1 GPU × 2 CPU) | 34 | 23 | 5 |
| Large (16 workers × 4 CPU + 2 GPU × 2 CPU) | 68 | 47 | 11 |

On the **reference** cluster, the formula gives **5** actors (conservative). This example’s **default `NUM_ACTORS` of 6** was tested on that hardware and uses slightly more than the nominal 70% Docling share (~71% of cluster CPUs for Docling alone). Treat the formula as a safe baseline when porting to a new cluster; raise `NUM_ACTORS` gradually while watching Ray Dashboard CPU utilization and job progress.

Also align **`REPARTITION_FACTOR`** with how much parallelism you want between Docling and embedding: higher factors create more blocks (and more shuffle) relative to Docling output — useful on larger clusters if stages otherwise bottleneck on partition count.

### Repartition tuning

`REPARTITION_FACTOR` controls how many blocks each actor's output is split
into before the embedding stage (`target_blocks = NUM_ACTORS × REPARTITION_FACTOR`).

- **When it helps:** Few large input blocks where each PDF produces many chunks.
  Repartitioning spreads work evenly across embedding and Milvus-write stages.
- **When it hurts:** The default workload is already well-distributed (many
  small PDFs), or the cluster has limited CPU headroom. Each repartition
  creates reduce tasks that compete for CPU slots; too many can trigger
  deadlock on small clusters.

The default `REPARTITION_FACTOR=2` produces `6 × 2 = 12` blocks, which
schedules comfortably on the reference hardware's ~10-CPU headroom.

## Observability

### Dashboard access

**Primary (CodeFlare SDK):** After creating or connecting to the cluster in
the notebook, the dashboard URL is available via:

```python
print(cluster.cluster_dashboard_uri())
```

This resolves automatically via HTTPRoute (RHOAI v3.0+), OpenShift Route,
or Ingress depending on the platform.

**Fallback (port-forward):** For non-RHOAI environments or manual access:

```bash
oc port-forward svc/<cluster-name>-head-svc 8265:8265 -n <namespace>
# Open http://localhost:8265
```

Useful views while the job runs:

- **Jobs** — submission status, logs, duration
- **Actors** — live DoclingChunkActor / MilvusWriteActor instances and their state
- **Metrics** — CPU, GPU, and object store utilization across workers

## Troubleshooting

### RayJob not starting

```bash
oc get rayjob <job-name> -n <namespace> -o yaml
oc get pods -l ray.io/cluster=<cluster-name> -n <namespace>
```

### PVC access errors

Verify the PVC has `ReadWriteMany` access mode:

```bash
oc get pvc <pvc-name> -n <namespace> -o jsonpath='{.spec.accessModes}'
```

### Milvus connection refused

Check that the Milvus service is reachable from the Ray cluster:

```bash
oc exec -it <head-pod> -n <namespace> -- curl -s http://<milvus-host>:<port>/v1/vector/collections
```

### vLLM GPU out-of-memory

On smaller GPUs (e.g. Tesla T4, 16 GB), CUDA graph capture can exhaust VRAM.
Set `VLLM_ENGINE_KWARGS_JSON={"enforce_eager": true, "gpu_memory_utilization": 0.8}`
in the ingestion notebook to disable graph capture and reduce memory usage.

### Actor memory errors

Reduce `NUM_ACTORS` or increase worker memory in the RayCluster spec.
Large/complex PDFs can require 2–4 Gi per Docling actor.

### CodeFlare SDK secret size exceeded

If the RayJob submission fails with "Secret size exceeds 1MB limit", ensure
the notebook's `working_dir` points to a minimal directory containing only
`docling_milvus_process.py` (the notebook handles this automatically).

### Pipeline stuck with no errors

If the pipeline appears hung with no error messages, check for resource deadlock
or backpressure using the Ray tasks API:

```bash
# Get task states from the Ray head node
oc exec -it <head-pod> -n <namespace> -- \
  curl -s http://localhost:8265/api/v0/tasks | python3 -m json.tool
```

Look for:

- **`PENDING_NODE_ASSIGNMENT`** — tasks cannot be scheduled because all CPUs are
  reserved by running actors. Reduce `NUM_ACTORS` (see "Sizing for your hardware").
- **`backpressured:tasks(ResourceBudget)`** — Ray Data is throttling new tasks
  because downstream stages are slower than upstream. This is normal behavior but
  if throughput is near zero, reduce `REPARTITION_FACTOR` to lower the number of
  concurrent reduce tasks competing for CPU headroom.

With the default configuration (`NUM_ACTORS=6`, `REPARTITION_FACTOR=2`), the
reference hardware (34 CPUs) has ~10 CPUs of headroom for scheduling overhead,
MilvusWriteActors, repartition reduce tasks, and Ray Data executor.

## Related examples

- **[Distributed PDF Processing with Docling](../../docling/)** — batch
  PDF-to-JSON/Markdown conversion without the RAG stack
