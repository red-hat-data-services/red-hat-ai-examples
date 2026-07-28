# RAG Document Processing Pipeline

End-to-end Retrieval-Augmented Generation (RAG) pipeline on OpenShift AI that processes PDF documents, ingests them into Milvus, deploys an LLM, and enables question-answering over the ingested content.

## Quick Links

- **New to this project?** Start with [Setup](#setup) below
- **Build & deploy the pipeline?** Open [rag_pipeline_build.ipynb](build_rag_pipeline/rag_pipeline_build.ipynb)
- **Test RAG queries?** Open [rag_query_test.ipynb](test/rag_query_test.ipynb)
- **Streaming with OGX?** Open [rag_ogx_streaming.ipynb](ogx_test/rag_ogx_streaming.ipynb)
- **Customizing parameters?** See [Configuration](#configuration) below

## Pipelines

This example provides **two pipeline variants**:

### 1. Single-Step Pipeline (`pipeline.py` / `rag_pipeline.yaml`)

All-in-one: parse, chunk, embed, and ingest into Milvus in a single RayJob. PVC is read-only. Best for simple deployments.

```text
PDF (PVC) --> [RayJob: Docling + chunk + embed + Milvus insert] --> Deploy LLM
```

### 2. Multi-Step Pipeline (`pipeline_multistep.py` / `rag_multistep_pipeline.yaml`)

Three reusable components with clear separation of concerns. Uses a local sentence-transformers model for embedding (no external embedding service needed). Best for production use and component reuse across pipelines.

```text
Step 1: Parse & Chunk PDFs
    (RayJob: Docling + HybridChunker -> JSONL on S3/MinIO)
                |
Step 2: Ingest into Milvus
    (read chunks from S3, embed locally with sentence-transformers, insert vectors)
                |
Step 3: Deploy LLM (vLLM InferenceService)
```

Steps run sequentially: parse, then ingest, then deploy.

## Architecture

```text
                    +-------------------+
                    |   PDF Documents   |
                    |      (PVC)        |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Parse & Chunk    |
                    |  (RayJob/Docling) |
                    |  -> JSONL on S3   |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Ingest to Milvus |
                    |  (local embed +   |
                    |   insert vectors) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |      Milvus       |
                    |  (vector store)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+         +---------v---------+
    |  Query embedding  |         |   vLLM Model      |
    |  (MiniLM local)   |         |  (InferenceService)|
    +---------+---------+         +---------+---------+
              |                             |
              +--------------+--------------+
                             |
                    +--------v----------+
                    |    RAG Answer      |
                    +-------------------+
```

## Directory Structure

```text
rag/
+-- build_rag_pipeline/
|   +-- rag_pipeline_build.ipynb   # Setup, compile, and deploy the pipeline
|   +-- rag_setup.py               # K8s helper utilities for the pipeline
+-- test/
|   +-- rag_query_test.ipynb       # Test RAG queries against deployed services
+-- ogx_test/
|   +-- rag_ogx_streaming.ipynb    # RAG with OpenGenAI Stack (OGX) streaming
+-- pipeline_multistep.py          # Multi-step pipeline definition
+-- README.md
```

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| OpenShift cluster | 4.14+ | With OpenShift AI (RHOAI) installed |
| KubeRay Operator | >= 1.1.0 | Manages RayJob / RayCluster CRDs |
| Milvus | >= 2.4.0 | Via Milvus Operator on OpenShift |
| MinIO / S3 | — | For intermediate chunk storage (multi-step pipeline) |
| KServe | Included in RHOAI | For InferenceService / vLLM runtime |
| GPU nodes | 1+ NVIDIA GPU | For vLLM model serving |
| PVC (ReadOnlyMany or RWX) | — | Contains input PDFs at `<mount>/input/pdfs/` |
| Python | 3.11+ | For running the notebook locally |

### Python packages (notebook host)

```text
codeflare-sdk>=0.25.0
kubernetes>=28.1.0
ray[default]>=2.44.1
pymilvus>=2.4.0
sentence-transformers>=2.2.0
openai>=1.0.0
```

### Container image

The Ray worker image must have Docling pre-installed:

```text
quay.io/rhoai-szaher/docling-ray:latest
```

## Setup

### 1. Apply RBAC

The pipeline service account needs permissions to create RayJobs, InferenceServices, and related resources. Apply the RBAC manifests before running the pipeline:

```bash
# Check your pipeline service account name
oc get sa -n ray-docling | grep -E 'pipeline|dspa'

# If needed, edit manifests/rbac.yaml to match your SA name
# Default: pipeline-runner-dspa

# Apply RBAC
oc apply -f manifests/rbac.yaml
```

The Role grants:

- `ray.io/rayjobs`, `ray.io/rayclusters` — create, get, patch, delete (for RayJob submission)
- `serving.kserve.io/inferenceservices` — create, get, patch, delete (for model deployment)
- `serving.kserve.io/servingruntimes` — get, list (to verify runtime availability)
- `secrets` — create, get, patch, delete (codeflare-sdk stores working directory as a Secret)
- `pods`, `pods/log`, `events` — get, list, watch (for monitoring)

### 2. Create S3 (MinIO) credentials Secret

The pipeline reads S3 credentials from a Kubernetes Secret.

**Option 1: Create from command line (RECOMMENDED)**

```bash
oc create secret generic minio-secret \
  --from-literal=access_key=<your-access-key> \
  --from-literal=secret_key=<your-secret-key> \
  -n ray-docling
```

**Option 2: Use the template file**

```bash
# For development/testing with default MinIO:
oc create secret generic minio-secret \
  --from-literal=access_key=minioadmin \
  --from-literal=secret_key=minioadmin \
  -n ray-docling
```

⚠️ **Security Note**: The `manifests/minio-secret.yaml` is a template with placeholder values. **Never commit actual credentials to git.** See the file header for instructions.

The Secret name defaults to `minio-secret` and can be overridden via the `s3_secret_name` pipeline parameter.

### 3. Create HuggingFace Token Secret (Optional)

If you are deploying a **gated model** (e.g., Mistral, Llama), create a Secret with your HuggingFace API token. The pipeline mounts this token into the model-download pod — if the Secret is missing, the pod won't be able to pull the model weights.

```bash
oc create secret generic hf-token-secret \
  --from-literal=token=<your-huggingface-token> \
  -n ray-docling
```

The Secret name defaults to `hf-token-secret` and can be overridden via the `hf_secret_name` pipeline parameter. Skip this step if your model is public (non-gated).

### 4. Verify prerequisites

**Automated validation (RECOMMENDED):**

```bash
cd /path/to/rag-ray
./scripts/validate_prerequisites.sh
```

This script checks:

- ✓ Namespace exists
- ✓ PVCs (data-pvc, model-cache-pvc) are bound
- ✓ MinIO/S3 service and credentials
- ✓ Milvus service
- ✓ KubeRay operator
- ✓ Data Science Pipelines (DSPA)
- ✓ Service account permissions
- ✓ GPU nodes (for LLM)

**Manual verification:**

```bash
# KubeRay operator running
oc get deployment kuberay-operator -n openshift-operators

# Milvus reachable
oc exec -it <any-pod> -n ray-docling -- curl -s http://milvus-milvus.milvus.svc.cluster.local:19530/v1/vector/collections

# MinIO reachable
oc exec -it <any-pod> -n ray-docling -- curl -s http://minio-service.default.svc.cluster.local:9000/minio/health/live

# PVC with PDFs exists
oc get pvc data-pvc -n ray-docling
```

## Quick Start

### Import via KFP UI

Upload `rag_multistep_pipeline.yaml` (or `rag_pipeline.yaml` for single-step) directly to the Data Science Pipelines UI:

1. Go to **Pipelines** > **Import pipeline**
2. Upload the YAML file
3. Configure parameters and create a run

### Compile from source

```bash
# Multi-step pipeline
python pipeline_multistep.py
# Output: rag_multistep_pipeline.yaml

# Single-step pipeline
python pipeline.py
# Output: rag_pipeline.yaml
```

### Standalone scripts

```bash
# Parse & chunk (write JSONL to S3/MinIO)
export PVC_MOUNT_PATH=/mnt/data INPUT_PATH=input/pdfs
export S3_ENDPOINT=http://minio-service.default.svc.cluster.local:9000
export S3_BUCKET=rag-chunks S3_ACCESS_KEY=minioadmin S3_SECRET_KEY=minioadmin
python scripts/docling_chunk_process.py

# Ingest into Milvus (read chunks from S3)
export MILVUS_HOST=milvus-milvus.milvus.svc.cluster.local
export S3_ENDPOINT=http://minio-service.default.svc.cluster.local:9000
export S3_BUCKET=rag-chunks S3_ACCESS_KEY=minioadmin S3_SECRET_KEY=minioadmin
python scripts/milvus_ingest.py

# RAG query
export INFERENCE_URL=https://your-model-endpoint/v1 MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
python scripts/rag_query.py "What is the main topic of the documents?"
```

## Configuration

### Multi-Step Pipeline Defaults

| Parameter | Default | Description |
|---|---|---|
| `num_files` | `1000` | Number of PDFs to process (0 = all) |
| `pvc_name` | `data-pvc` | PVC name |
| `input_path` | `input/pdfs` | Input PDF path on PVC |
| `s3_endpoint` | `http://minio-service.default.svc.cluster.local:9000` | S3/MinIO endpoint |
| `s3_bucket` | `rag-chunks` | S3 bucket for intermediate chunks |
| `s3_prefix` | `chunks` | S3 key prefix for chunk files |
| `embedding_model` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `embedding_dim` | `384` | Embedding vector dimension |
| `chunk_max_tokens` | `256` | Max tokens per chunk |
| `num_workers` | `2` | Ray worker pods |
| `worker_cpus` | `8` | CPUs per worker |
| `worker_memory_gb` | `16` | Memory per worker |
| `cpus_per_actor` | `4` | CPUs per Docling actor |
| `min_actors` | `2` | Min actor pool size |
| `max_actors` | `4` | Max actor pool size |
| `milvus_host` | `milvus-milvus.milvus.svc.cluster.local` | Milvus hostname |
| `collection_name` | `rag_documents` | Milvus collection |
| `llm_model_name` | `mistralai/Mistral-7B-Instruct-v0.3` | LLM model |
| `gpu_count` | `1` | GPUs for LLM |

## Milvus Collection Schema

| Field | Type | Description |
|---|---|---|
| `id` | INT64 (auto) | Primary key |
| `source_file` | VARCHAR(512) | Source PDF filename |
| `chunk_index` | INT64 | Chunk position within the document |
| `text` | VARCHAR(8192) | Chunk text content |
| `embedding` | FLOAT_VECTOR(384) | Normalized embedding vector |

Index: `IVF_FLAT` with `COSINE` metric and `nlist=128`.

## Design Decisions

- **Multi-step separation:** Each component has a single responsibility. PDF parsing, Milvus ingestion, and LLM deployment are independent, reusable components that can be mixed into different pipelines.
- **S3 intermediate storage:** Chunks are stored as JSONL in S3 (MinIO) between the parse and ingest steps. This avoids needing a ReadWriteMany PVC (which requires NFS/CephFS), provides a checkpoint if ingestion fails, and keeps the input PVC read-only.
- **Local embedding:** The ingest component uses a local `sentence-transformers/all-MiniLM-L6-v2` model (~80MB) for embedding. No external embedding service or TEI runtime is needed. The component also supports an optional `embedding_endpoint` for deployed embedding services.
- **Subprocess isolation:** Each Ray actor runs Docling in a separate subprocess for crash isolation and timeout handling.
- **HybridChunker:** Structure-aware chunking that respects document structure (headings, paragraphs, tables) rather than splitting on arbitrary character boundaries.
- **Head node exclusion:** RayJob patches `num-cpus=0` on the head node, reserving it for coordination.
- **1000 PDF default:** The multi-step pipeline defaults to processing 1000 PDFs, a practical demo size.

## Troubleshooting

### RayJob stays in PENDING

Check that the KubeRay operator is running and that the namespace has enough CPU/memory quota for the requested workers.

### Milvus connection refused

Verify Milvus is running and reachable:

```bash
oc exec -it <pod> -n <namespace> -- python -c "
from pymilvus import MilvusClient
c = MilvusClient(uri='http://milvus-milvus.milvus.svc.cluster.local:19530')
print(c.list_collections())
"
```

### Model deployment timeout

The LLM InferenceService waits up to 30 minutes. Ensure the ServingRuntime CR (`vllm-runtime`) exists and GPU nodes are available.

### Actors crashing with OOM

Increase `worker_memory_gb` or reduce `batch_size`. Large PDFs with many images consume significant memory during Docling parsing.
