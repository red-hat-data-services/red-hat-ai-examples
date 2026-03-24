# RAG Document Ingestion with Ray Data

Ingest PDFs into a Milvus vector database for RAG using Ray Data, Docling,
and sentence-transformers. The pipeline runs as a RayJob on an existing
RayCluster on OpenShift.

## Quick Start

1. Open `rag_ingestion.ipynb` in your RHOAI workbench
2. Run every cell top-to-bottom: configure, review the pipeline code,
   submit the RayJob, monitor, and validate

## Prerequisites

- Red Hat OpenShift AI with KubeRay operator
- Existing RayCluster (see `manifests/raycluster-rag-optimized.yaml`)
- ReadWriteMany PVC with input PDFs mounted on all Ray workers
- Milvus accessible from the Ray cluster
- CodeFlare SDK (`pip install codeflare-sdk`)

## Files

| File | Description |
|------|-------------|
| `rag_ingestion.ipynb` | Main notebook -- walks through the pipeline, then submits it |
| `docling_milvus_process.py` | RayJob entrypoint (3-stage Ray Data pipeline) |
| `manifests/raycluster-rag-optimized.yaml` | RayCluster spec (CPU workers) |
