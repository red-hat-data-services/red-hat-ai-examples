# RAG Pipelines with Ray Data

Distributed RAG ingestion pipelines on Red Hat OpenShift AI -- parse PDFs
with Docling, generate embeddings, and store vectors in Milvus.

## Pipelines

- **[Ray Data Pipeline](ray-data-pipeline/)** — 3-stage streaming pipeline using
  Ray Data `map_batches` with Docling, vLLM embedding, and Milvus
- **Kubeflow Pipeline** — *(coming soon)* Kubeflow Pipelines orchestration of the
  same RAG ingestion stages

## Related examples

- **[Distributed PDF Processing with Docling](../docling/)** -- batch
  PDF-to-JSON/Markdown conversion without the RAG stack
