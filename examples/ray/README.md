# Ray Examples

Examples using [Ray](https://www.ray.io/) on Red Hat OpenShift AI for
distributed data processing and AI workloads.

## Data Processing

| Example | Description |
|---------|-------------|
| [**RAG with Ray Data**](data/rag/) | RAG ingestion pipeline: parse PDFs with Docling, embed with vLLM via `vLLMEngineProcessorConfig`, store in Milvus |
| [Distributed PDF Processing](data/docling/) | Batch PDF-to-JSON/Markdown conversion with Ray Data and Docling |
