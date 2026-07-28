# Knowledge Tuning Pipeline for Kubeflow Pipelines

## Overview

This Kubeflow Pipelines (KFP) example shows how to use Kubeflow pipelines to automate the steps in the [Knowledge Tuning example](../README.md). By using pipelines, you can run long training jobs or retrain your models on a schedule without having to manually run them in a notebook.

The Knowledge Tuning example uses notebooks to implement a workflow that processes documents, generates synthetic training data using multiple knowledge generation strategies, mixes the generated datasets, and fine-tunes a student model.

This Kubeflow Pipelines example converts the steps into KFP (Kubeflow Pipelines) components for production use. The example is structured with independent components at the step level for easier debugging. The example provides defaults for the flows and parameters. Optionally, you can customize the parameter values and the model.

### About the example pipeline workflow

The pipeline follows the Knowledge Tuning example workflow as shown in the following figure:

Figure 1. End-to-end workflow overview

![End-to-end workflow overview diagram](../../../assets/usecase/knowledge-tuning/Overall%20Flow.png)

### Pipeline components

The `Kubeflow_Pipline/components` subfolder has python files for each component in the Knowledge Tuning workflow:

**Data Processing**

Downloads Docling models (cached) and processes documents from web URLs or local files:

- Converts PDF/HTML to Markdown
- Chunks documents with configurable token limits
- Adds domain-specific context and ICL (In-Context Learning) examples

Example python files: `document_processing.py`, `download_docling_models.py`

Source repository:  `opendatahub-io/data-processing`

Base image: `quay.io/fabianofranz/docling-ubi9:2.54.0`

Packages: `torch`, `datasets`, `docling`, `tiktoken`

**Knowledge Generation**

Generates four types of synthetic training data in parallel:

- Detailed summaries: Comprehensive summaries with Q&A pairs
- Extractive summaries: Direct extracts from documents with Q&A (runs sequentially)
- Key facts summary: Focuses on key facts and concepts
- Document-based Q&A: Question-answer pairs based on document content

Merges all datasets after generation.

Example python file: `knowledge_generation.py`

Source repository: `red-hat-data-services/red-hat-ai-examples`

Base image: `quay.io/fabianofranz/docling-ubi9:2.54.0`

Packages: `nest-asyncio`, `sdg-hub`, `datasets`

**Knowledge Mixing**

Processes and combines the generated datasets:

- Samples Q&A pairs based on configurable cut sizes
- Tokenizes content using the student model tokenizer
- Validates and filters data
- Creates training-ready JSONL files in chat format
- Selects the optimal dataset (largest feasible cut size)

Example python file: `knowledge_mixing.py`

Source repository: Not applicable. This is a custom component.

Base image: `quay.io/opendatahub/odh-training-th04-cpu-torch29-py312-rhel9:cpu-3.3`

Packages: `polars`, `transformers`, `torch`

**Model Fine-tuning**

Fine-tunes a student model by using the mixed knowledge dataset:

- Supervised Fine-Tuning (SFT)
- Configurable GPU/memory resources
- Multi-epoch training with batch size control

This is a reusable  prebuilt component that is managed by the Kubeflow pipelines team.

Source repository: `red-hat-data-services/pipelines-components`

## Prepare the example pipeline

### Procedure

1. Clone the example repository.

   a. To clone the example repository to your local environment, run the following command in a terminal window:

      ```bash
      git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
      ```

   b. Set your working directory to the `Kubeflow_Pipeline` folder:

      ```bash
      cd red-hat-ai-examples/examples/knowledge-tuning/Kubeflow_Pipeline
      ```

2. Set up the Python environment.

   Run the following commands to install these required packages:

   - `kfp>=2.16.1`
   - `kfp-kubernetes>=2.16.1`
   - `kfp-components @ git+https://github.com/red-hat-data-services/pipelines-components@main`

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -e .
   ```

3. To use the example pipeline with its default configuration, skip to Step 4.

   If you want to customize the pipeline configuration, edit the `pipeline.py` file and change the following values:

   - Document URLs
   - Model endpoints and credentials
   - Default parameters

   See _Customize the pipeline configuration_ for details on the parameter values that you can change.

4. Compile the pipeline:

   Before you can define your pipeline in the cluster, you must convert your Python-defined pipeline into YAML format. You can use the Kubeflow Pipelines Software Development Kit to compile your pipeline code into a deployable YAML file for declarative GitOps deployment:

   ```bash
   python pipeline.py
   ```

### Verification

The result of the python `pipeline.py` command is the `knowledge_tuning_pipeline.yaml` file.

## Import and run the example pipeline

After you compile the pipeline, you can import the YAML file and deploy it in OpenShift AI. The imported YAML file visualizes the pipeline flow.

### Prerequisites

- Make sure that the `nfs-csi` storage class is available on your cluster.

- For workspace storage, KFP uses the pipeline configuration to automatically create a PVC with the following configuration:

  | Configuration | Value |
  |--------------|-------|
  | **Size** | 80Gi |
  | **Storage Class** | nfs-csi |
  | **Access Modes** | ReadWriteMany |

  In the OpenShift console, select **Storage** > **StorageClasses**. Verify that `nfs-csi` is listed.

- Confirm that your cluster has the following resources required by the kubeflow pipeline components:

  | Stage | CPU | Memory | GPU | Storage |
  |-------|-----|--------|-----|---------|
  | Document Processing | 2-4 cores | 8-16 GB | 0 | ~5 GB |
  | Knowledge Generation | 2-4 cores | 8-16 GB | 0 (uses API) | ~10 GB |
  | Knowledge Mixing | 4-8 cores | 16-32 GB | 0 | ~20 GB |
  | Model Training | 8-16 cores | 40+ GB | 8 | ~30 GB |

- Create a Kubernetes secret named `kubernetes-credentials` with the following keys:

  | Secret Key | Description | Required |
  |------------|-------------|----------|
  | `KUBERNETES_SERVER_URL` | Kubernetes API server URL | Yes |
  | `KUBERNETES_AUTH_TOKEN` | Authentication token for Kubernetes API | Yes |
  | `HF_TOKEN` | HuggingFace token for model downloads | Yes |

  ```bash
  kubectl create secret generic kubernetes-credentials \
    --from-literal=KUBERNETES_SERVER_URL="https://api.your-cluster.com:6443" \
    --from-literal=KUBERNETES_AUTH_TOKEN="your-k8s-token" \
    --from-literal=HF_TOKEN="your-huggingface-token" \
    -n <your-namespace>
  ```

- You have configured a pipeline server in OpenShift AI, as described in [Configuring a pipeline server in the Red Hat OpenShift AI documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html-single/working_with_ai_pipelines/index#configuring-a-pipeline-server_ai-pipelines).

### Procedure

1. Import the pipeline, as described in [Importing a pipeline](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html-single/working_with_ai_pipelines/index#importing-a-pipeline_ai-pipelines).

2. Run the pipeline in OpenShift AI, as described in [Executing a pipeline run](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html-single/working_with_ai_pipelines/index#executing-a-pipeline-run_ai-pipelines).

## Troubleshoot

Use the following information to help troubleshoot problems that you might encounter when you run the example pipeline:

**PVC not created or insufficient storage**

- **Solution:** Verify that the storage class `nfs-csi` exists and that it supports the `ReadWriteMany` access mode.

- **Alternative:** Modify `PVC_STORAGE_CLASS` in the `pipeline.py` file.

**Inference timeouts during knowledge generation**

- **Solution:** Increase the `inference_timeout` parameter (default: `2500s`) for the Knowledge Generation component.

- **Alternative:** Reduce the value of the `max_concurrency` parameter to lower the API load.

**Out of memory during training**

- **Solution:** Increase the value of the `training_resource_memory_per_worker` parameter for the Model Training component.

- **Alternative:** Reduce the value of the `training_effective_batch_size` parameter for the Model Training component.

**Cut size validation warnings**

- **Solution:** Reduce the value of the `cut_size` parameter for the Knowledge Mixing component.

- **Details:** Pipeline validates that sufficient summaries exist per raw document

**Missing HuggingFace models**

- **Solution:** Verify that the `HF_TOKEN` is correct in the `kubernetes-credentials` secret

- **Alternative:** Use a publicly-accessible model.

## Customize the pipeline

You can customize the pipeline by changing the values of the parameters and environment variables listed in the following tables.

Here are some optimization tips:

- **Caching:** The Docling model download is cached. You can reuse artifacts across runs.
- **Concurrency:** Adjust `max_concurrency` based on inference server capacity.
- **Subsample:** Use `seed_data_subsample` for testing with smaller datasets.
- **Cut Sizes:** Start with smaller cut sizes (1,5) before using larger values (10+).
- **Reasoning:** Disable `enable_reasoning` for faster generation with simpler outputs.

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

### Environment Variables

| Variable | Set Automatically by this component| Purpose |
|----------|--------|---------|
| `LITELLM_REQUEST_TIMEOUT` | Knowledge Generation | API request timeout configuration |
| `HF_HOME` | Knowledge Mixing | HuggingFace cache directory |
| `DOCLING_CACHE_DIR` | Document Processing | Docling model cache location |
