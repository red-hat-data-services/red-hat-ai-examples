# Knowledge Tuning Pipeline for Kubeflow Pipelines

## Overview

This Kubeflow Pipelines (KFP) implementation provides an end-to-end knowledge tuning workflow that processes documents, generates synthetic training data using multiple knowledge generation strategies, mixes the generated datasets, and fine-tunes a student model. The pipeline leverages state-of-the-art tools like Docling for document processing and SDG Hub for synthetic data generation.

## Component Examples

This pipeline integrates components from multiple external repositories:

| Component | Source Repository | Description | Reusable |
|-----------|------------------|-------------|-------------|
| **Document Processing** | [opendatahub-io/data-processing](https://github.com/opendatahub-io/data-processing/tree/main/kubeflow-pipelines/docling-standard) | Document preprocessing using Docling for PDF/HTML parsing and chunking | ❌ |
| **Knowledge Generation** | [red-hat-data-services/red-hat-ai-examples](https://github.com/red-hat-data-services/red-hat-ai-examples/tree/main/examples/domain_customization_kfp_pipeline) | SDG Hub-based synthetic data generation | ❌ |
| **Knowledge Mixing** | None | Custom component for knowledge mixing | ❌ |
| **Model Training** | [red-hat-data-services/pipelines-components](https://github.com/red-hat-data-services/pipelines-components/tree/main/components/training/finetuning) | Supervised fine-tuning component for model training | ✅ |

## Pipeline Stages

### Stage 1: Document Processing

Downloads Docling models (cached) and processes documents from web URLs or local files:

- Converts PDF/HTML to Markdown
- Chunks documents with configurable token limits
- Adds domain-specific context and ICL (In-Context Learning) examples

### Stage 2: Knowledge Generation

Generates four types of synthetic training data in parallel:

1. **Detailed Summaries**: Comprehensive summaries with Q&A pairs
2. **Extractive Summaries**: Direct extracts from documents with Q&A (runs sequentially)
3. **Key Facts Summary**: Focuses on key facts and concepts
4. **Document-based Q&A**: Question-answer pairs based on document content

All datasets are merged after generation.

### Stage 3: Knowledge Mixing

Processes and combines the generated datasets:

- Samples Q&A pairs based on configurable cut sizes
- Tokenizes content using the student model tokenizer
- Validates and filters data
- Creates training-ready JSONL files in chat format
- Selects the optimal dataset (largest feasible cut size)

### Stage 4: Model Fine-tuning

Fine-tunes a student model using the mixed knowledge dataset:

- Supervised Fine-Tuning (SFT)
- Configurable GPU/memory resources
- Multi-epoch training with batch size control

## Pipeline Parameters

### Document Processing Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunk_max_tokens` | int | 512 | Maximum tokens per document chunk |
| `chunk_overlap_tokens` | int | 50 | Overlapping tokens between consecutive chunks |
| `web_urls` | str | "None" | List of web urls separated by , |
| `domain` | str | "None" | Domain context for the documents |
| `domain_outline` | str | "None" | Outline or structure of the domain |
| `icl_document` | str | "None" | In-context learning example document |
| `icl_query1` | str | "None" | In-context learning example query 1 |
| `icl_query2` | str | "None" | In-context learning example query 2 |
| `icl_query3` | str | "None" | In-context learning example query 3 |

### Knowledge Generation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | str | "openai/gpt-oss-20b" | Teacher model for synthetic data generation |
| `api_key` | str | (JWT token) | API key/token for model inference |
| `api_base` | str | (OpenShift URL) | Base URL for the inference API endpoint |
| `seed_data_subsample` | int | 0 | Number of documents to subsample (0 = all) |
| `enable_reasoning` | bool | True | Enable reasoning/thinking in generated responses |
| `number_of_summaries` | int | 1 | Number of summary variations per document |
| `max_concurrency` | int | 5 | Maximum concurrent API requests |
| `inference_timeout` | int | 2500 | API request timeout in seconds |

### Knowledge Mixing Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tokenizer_model_name` | str | "Qwen/Qwen2.5-1.5B-Instruct" | Tokenizer model for token counting |
| `cut_size` | str | "1,5,10" | Comma-separated cut sizes (summaries per raw doc) |
| `qa_per_doc` | int | 3 | Maximum Q&A pairs per document/summary |
| `save_gpt_oss_format` | bool | False | Apply GPT-OSS specific filtering |

### Model Training Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `student_model_name` | str | "Qwen/Qwen2.5-1.5B-Instruct" | Base model to fine-tune |
| `training_resource_gpu_per_worker` | int | 8 | Number of GPUs per training worker |
| `training_num_epochs` | int | 1 | Number of training epochs |
| `training_effective_batch_size` | int | 32 | Effective batch size for training |
| `training_resource_memory_per_worker` | str | "40Gi" | Memory allocation per worker |

## Prerequisites

### 1. Persistent Volume Claim (PVC)

The pipeline requires a shared PVC for workspace storage:

| Configuration | Value |
|--------------|-------|
| **Size** | 80Gi |
| **Storage Class** | nfs-csi |
| **Access Modes** | ReadWriteMany |

**Note**: The PVC is automatically created by KFP using the pipeline configuration. Ensure your cluster supports the specified storage class.

### 2. Kubernetes Secret

Create a Kubernetes secret named `kubernetes-credentials` with the following keys:

| Secret Key | Description | Required |
|------------|-------------|----------|
| `KUBERNETES_SERVER_URL` | Kubernetes API server URL | Yes |
| `KUBERNETES_AUTH_TOKEN` | Authentication token for Kubernetes API | Yes |
| `HF_TOKEN` | HuggingFace token for model downloads | Yes |

**Create the secret:**

```bash
kubectl create secret generic kubernetes-credentials \
  --from-literal=KUBERNETES_SERVER_URL="https://api.your-cluster.com:6443" \
  --from-literal=KUBERNETES_AUTH_TOKEN="your-k8s-token" \
  --from-literal=HF_TOKEN="your-huggingface-token" \
  -n <your-namespace>
```

### 3. Environment Variables

The following environment variables are set automatically by components:

| Variable | Set By | Purpose |
|----------|--------|---------|
| `LITELLM_REQUEST_TIMEOUT` | Knowledge Generation | API request timeout configuration |
| `HF_HOME` | Knowledge Mixing | HuggingFace cache directory |
| `DOCLING_CACHE_DIR` | Document Processing | Docling model cache location |

### 4. Base Container Images

The pipeline uses the following container images:

| Component | Base Image | Packages |
|-----------|-----------|----------|
| Document Processing | `quay.io/fabianofranz/docling-ubi9:2.54.0` | torch, datasets, docling, tiktoken |
| Knowledge Generation | `quay.io/fabianofranz/docling-ubi9:2.54.0` | nest-asyncio, sdg-hub, datasets |
| Knowledge Mixing | `quay.io/opendatahub/odh-training-th04-cpu-torch29-py312-rhel9:cpu-3.3` | polars, transformers, torch |
| Model Training | From kfp-components | (Managed by component) |

### 5. Python Dependencies

Install the pipeline dependencies:

```bash
pip install -e .
```

Required packages (from `pyproject.toml`):

- `kfp==2.15.2`
- `kfp-kubernetes>=2.15.2`
- `kfp-components @ git+https://github.com/red-hat-data-services/pipelines-components@main`

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
cd red-hat-ai-examples/examples/knowledge-tuning/kfp
```

### 2. Set Up Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Configure Your Pipeline

Edit `pipeline.py` to customize:

- Document URLs
- Model endpoints and credentials
- Default parameters

### 4. Compile the Pipeline

```bash
python pipeline.py
```

This generates `knowledge_tuning_pipeline.yaml` which can be used for kubeflow pipeline deployment.

## Troubleshooting

### Common Issues

**Issue**: PVC not created or insufficient storage

- **Solution**: Verify storage class `nfs-csi` exists and supports ReadWriteMany
- **Alternative**: Modify `PVC_STORAGE_CLASS` in pipeline.py

**Issue**: Inference timeouts during knowledge generation

- **Solution**: Increase `inference_timeout` parameter (default: 2500s)
- **Alternative**: Reduce `max_concurrency` to lower API load

**Issue**: Out of memory during training

- **Solution**: Increase `training_resource_memory_per_worker`
- **Alternative**: Reduce `training_effective_batch_size`

**Issue**: Cut size validation warnings

- **Solution**: Reduce cut sizes in `cut_size` parameter
- **Details**: Pipeline validates that sufficient summaries exist per raw document

**Issue**: Missing HuggingFace models

- **Solution**: Verify `HF_TOKEN` in kubernetes-credentials secret
- **Alternative**: Use publicly accessible models

## Performance Considerations

### Resource Requirements

| Stage | CPU | Memory | GPU | Storage |
|-------|-----|--------|-----|---------|
| Document Processing | 2-4 cores | 8-16 GB | 0 | ~5 GB |
| Knowledge Generation | 2-4 cores | 8-16 GB | 0 (uses API) | ~10 GB |
| Knowledge Mixing | 4-8 cores | 16-32 GB | 0 | ~20 GB |
| Model Training | 8-16 cores | 40+ GB | 8 | ~30 GB |

### Optimization Tips

1. **Caching**: Docling model download is cached - reuse artifacts across runs
2. **Concurrency**: Adjust `max_concurrency` based on inference server capacity
3. **Subsample**: Use `seed_data_subsample` for testing with smaller datasets
4. **Cut Sizes**: Start with smaller cut sizes (1,5) before using larger values (10+)
5. **Reasoning**: Disable `enable_reasoning` for faster generation with simpler outputs

## Contributing

To modify or extend the pipeline:

1. Edit component files in `components/` directory
2. Update `pipeline.py` to include new components or parameters
3. Recompile the pipeline: `python pipeline.py`
4. Test with small datasets before full-scale runs
